# SPDX-FileCopyrightText: Copyright (c) 2021 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# Copyright (c) 2021 ETH Zurich, Nikita Rudin

import numpy as np

import code
import torch
import torch.nn as nn
from torch.distributions import Normal
from torch.nn.modules import rnn
from torch.nn.modules.activation import ReLU


DYNAMIC_ENV_GROUP_DIM = 15
DYNAMIC_ENV_TYPE_COLUMNS = {
    "hurdle": 1,
    "gap": 2,
    "step": 3,
    "tilted_pad": 4,
}


class StateHistoryEncoder(nn.Module):
    def __init__(
        self, activation_fn, input_size, tsteps, output_size, tanh_encoder_output=False
    ):
        # self.device = device
        super(StateHistoryEncoder, self).__init__()
        self.activation_fn = activation_fn
        self.tsteps = tsteps

        channel_size = 10
        # last_activation = nn.ELU()

        self.encoder = nn.Sequential(
            nn.Linear(input_size, 3 * channel_size),
            self.activation_fn,
        )

        if tsteps == 50:
            self.conv_layers = nn.Sequential(
                nn.Conv1d(
                    in_channels=3 * channel_size,
                    out_channels=2 * channel_size,
                    kernel_size=8,
                    stride=4,
                ),
                self.activation_fn,
                nn.Conv1d(
                    in_channels=2 * channel_size,
                    out_channels=channel_size,
                    kernel_size=5,
                    stride=1,
                ),
                self.activation_fn,
                nn.Conv1d(
                    in_channels=channel_size,
                    out_channels=channel_size,
                    kernel_size=5,
                    stride=1,
                ),
                self.activation_fn,
                nn.Flatten(),
            )
        elif tsteps == 10:
            self.conv_layers = nn.Sequential(
                nn.Conv1d(
                    in_channels=3 * channel_size,
                    out_channels=2 * channel_size,
                    kernel_size=4,
                    stride=2,
                ),
                self.activation_fn,
                nn.Conv1d(
                    in_channels=2 * channel_size,
                    out_channels=channel_size,
                    kernel_size=2,
                    stride=1,
                ),
                self.activation_fn,
                nn.Flatten(),
            )
        elif tsteps == 20:
            self.conv_layers = nn.Sequential(
                nn.Conv1d(
                    in_channels=3 * channel_size,
                    out_channels=2 * channel_size,
                    kernel_size=6,
                    stride=2,
                ),
                self.activation_fn,
                nn.Conv1d(
                    in_channels=2 * channel_size,
                    out_channels=channel_size,
                    kernel_size=4,
                    stride=2,
                ),
                self.activation_fn,
                nn.Flatten(),
            )
        else:
            raise (ValueError("tsteps must be 10, 20 or 50"))

        self.linear_output = nn.Sequential(
            nn.Linear(channel_size * 3, output_size), self.activation_fn
        )

    def forward(self, obs):
        # nd * T * n_proprio
        nd = obs.shape[0]
        T = self.tsteps
        # print("obs device", obs.device)
        # print("encoder device", next(self.encoder.parameters()).device)
        projection = self.encoder(
            obs.reshape([nd * T, -1])
        )  # do projection for n_proprio -> 32
        output = self.conv_layers(projection.reshape([nd, T, -1]).permute((0, 2, 1)))
        output = self.linear_output(output)
        return output


class Actor(nn.Module):
    def __init__(
        self,
        num_prop,
        num_scan,
        num_actions,
        scan_encoder_dims,
        actor_hidden_dims,
        priv_encoder_dims,
        num_priv_latent,
        num_priv_explicit,
        num_hist,
        activation,
        tanh_encoder_output=False,
        num_dynamic_env_latent=0,
        dynamic_env_latent_cfg=None,
    ) -> None:
        super().__init__()
        # prop -> scan -> priv_explicit -> priv_latent -> hist
        # actor input: prop -> scan -> priv_explicit -> latent
        self.num_prop = num_prop
        self.num_scan = num_scan
        self.num_hist = num_hist
        self.num_actions = num_actions
        self.num_priv_latent = num_priv_latent
        self.num_priv_explicit = num_priv_explicit
        self.num_dynamic_env_latent = num_dynamic_env_latent
        self.dynamic_env_group_dim = DYNAMIC_ENV_GROUP_DIM
        self.dynamic_env_num_groups = (
            num_dynamic_env_latent // self.dynamic_env_group_dim
            if num_dynamic_env_latent > 0
            else 0
        )
        self.dynamic_env_recovery_modes = self._parse_dynamic_recovery_modes(
            dynamic_env_latent_cfg
        )
        self.if_scan_encode = scan_encoder_dims is not None and num_scan > 0

        if len(priv_encoder_dims) > 0:
            priv_encoder_layers = []
            priv_encoder_layers.append(nn.Linear(num_priv_latent, priv_encoder_dims[0]))
            priv_encoder_layers.append(activation)
            for l in range(len(priv_encoder_dims) - 1):
                priv_encoder_layers.append(
                    nn.Linear(priv_encoder_dims[l], priv_encoder_dims[l + 1])
                )
                priv_encoder_layers.append(activation)
            self.priv_encoder = nn.Sequential(*priv_encoder_layers)
            priv_encoder_output_dim = priv_encoder_dims[-1]
        else:
            self.priv_encoder = nn.Identity()
            priv_encoder_output_dim = num_priv_latent

        self.history_encoder = StateHistoryEncoder(
            activation, num_prop, num_hist, priv_encoder_output_dim
        )
        if num_dynamic_env_latent > 0:
            self.dynamic_history_encoder = StateHistoryEncoder(
                activation, num_prop, num_hist, num_dynamic_env_latent
            )
        else:
            self.dynamic_history_encoder = None

        if self.if_scan_encode:
            scan_encoder = []
            scan_encoder.append(nn.Linear(num_scan, scan_encoder_dims[0]))
            scan_encoder.append(activation)
            for l in range(len(scan_encoder_dims) - 1):
                if l == len(scan_encoder_dims) - 2:
                    scan_encoder.append(
                        nn.Linear(scan_encoder_dims[l], scan_encoder_dims[l + 1])
                    )
                    scan_encoder.append(nn.Tanh())
                else:
                    scan_encoder.append(
                        nn.Linear(scan_encoder_dims[l], scan_encoder_dims[l + 1])
                    )
                    scan_encoder.append(activation)
            self.scan_encoder = nn.Sequential(*scan_encoder)
            self.scan_encoder_output_dim = scan_encoder_dims[-1]
        else:
            self.scan_encoder = nn.Identity()
            self.scan_encoder_output_dim = num_scan

        actor_layers = []
        actor_layers.append(
            nn.Linear(
                num_prop
                + self.scan_encoder_output_dim
                + num_priv_explicit
                + priv_encoder_output_dim
                + num_dynamic_env_latent,
                actor_hidden_dims[0],
            )
        )
        actor_layers.append(activation)
        for l in range(len(actor_hidden_dims)):
            if l == len(actor_hidden_dims) - 1:
                actor_layers.append(nn.Linear(actor_hidden_dims[l], num_actions))
            else:
                actor_layers.append(
                    nn.Linear(actor_hidden_dims[l], actor_hidden_dims[l + 1])
                )
                actor_layers.append(activation)
        if tanh_encoder_output:
            actor_layers.append(nn.Tanh())
        self.actor_backbone = nn.Sequential(*actor_layers)

    def _parse_dynamic_recovery_modes(self, cfg):
        modes = {name: "roa" for name in DYNAMIC_ENV_TYPE_COLUMNS}
        if cfg is None:
            return modes
        raw_modes = getattr(cfg, "recovery_modes", None)
        if raw_modes is None and isinstance(cfg, dict):
            raw_modes = cfg.get("recovery_modes")
        if raw_modes is not None:
            modes.update(raw_modes)
        for name, mode in modes.items():
            if mode not in ("roa", "teacher_student"):
                raise ValueError(
                    f"Unsupported dynamic env latent recovery mode for {name}: {mode}"
                )
        return modes

    def forward(
        self,
        obs,
        hist_encoding: bool,
        eval=False,
        scandots_latent=None,
        dynamic_env_latent=None,
    ):
        if self.if_scan_encode:
            obs_scan = obs[:, self.num_prop : self.num_prop + self.num_scan]
            if scandots_latent is None:
                scan_latent = self.scan_encoder(obs_scan)
            else:
                scan_latent = scandots_latent
            obs_prop_scan = torch.cat([obs[:, : self.num_prop], scan_latent], dim=1)
        else:
            obs_prop_scan = obs[:, : self.num_prop + self.num_scan]
        obs_priv_explicit = obs[
            :,
            self.num_prop
            + self.num_scan : self.num_prop
            + self.num_scan
            + self.num_priv_explicit,
        ]
        if hist_encoding:
            latent = self.infer_hist_latent(obs)
        else:
            latent = self.infer_priv_latent(obs)
        dynamic_latent = self.infer_dynamic_env_latent(
            obs, hist_encoding=hist_encoding, dynamic_env_latent=dynamic_env_latent
        )
        backbone_input = torch.cat(
            [obs_prop_scan, obs_priv_explicit, latent, dynamic_latent], dim=1
        )
        backbone_output = self.actor_backbone(backbone_input)
        return backbone_output

    def _dynamic_env_start(self):
        return (
            self.num_prop
            + self.num_scan
            + self.num_priv_explicit
            + self.num_priv_latent
        )

    def infer_priv_latent(self, obs):
        priv = obs[
            :,
            self.num_prop
            + self.num_scan
            + self.num_priv_explicit : self.num_prop
            + self.num_scan
            + self.num_priv_explicit
            + self.num_priv_latent,
        ]
        return self.priv_encoder(priv)

    def infer_hist_latent(self, obs):
        hist = obs[:, -self.num_hist * self.num_prop :]
        return self.history_encoder(hist.view(-1, self.num_hist, self.num_prop))

    def infer_priv_dynamic_env_latent(self, obs):
        if self.num_dynamic_env_latent == 0:
            return obs.new_zeros((obs.shape[0], 0))
        start = self._dynamic_env_start()
        return obs[:, start : start + self.num_dynamic_env_latent]

    def infer_hist_dynamic_env_latent(self, obs):
        if self.num_dynamic_env_latent == 0:
            return obs.new_zeros((obs.shape[0], 0))
        hist = obs[:, -self.num_hist * self.num_prop :]
        return self.dynamic_history_encoder(hist.view(-1, self.num_hist, self.num_prop))

    def dynamic_env_recovery_mask(self, obs, mode):
        if self.num_dynamic_env_latent == 0:
            return obs.new_zeros((obs.shape[0], 0), dtype=torch.bool)
        labels = self.infer_priv_dynamic_env_latent(obs).view(
            obs.shape[0], self.dynamic_env_num_groups, self.dynamic_env_group_dim
        )
        group_mask = labels[..., 0] > 0.5
        mode_mask = torch.zeros_like(group_mask)
        for name, column in DYNAMIC_ENV_TYPE_COLUMNS.items():
            if self.dynamic_env_recovery_modes.get(name) == mode:
                mode_mask |= labels[..., column] > 0.5
        group_mask &= mode_mask
        return (
            group_mask[:, :, None]
            .expand_as(labels)
            .reshape(obs.shape[0], self.num_dynamic_env_latent)
        )

    def infer_dynamic_env_latent(
        self, obs, hist_encoding: bool, dynamic_env_latent=None
    ):
        priv_dynamic = self.infer_priv_dynamic_env_latent(obs)
        if self.num_dynamic_env_latent == 0:
            return priv_dynamic
        output = priv_dynamic
        if hist_encoding:
            hist_dynamic = self.infer_hist_dynamic_env_latent(obs)
            roa_mask = self.dynamic_env_recovery_mask(obs, "roa")
            output = torch.where(roa_mask, hist_dynamic, output)
        if dynamic_env_latent is not None:
            teacher_student_mask = self.dynamic_env_recovery_mask(
                obs, "teacher_student"
            )
            output = torch.where(teacher_student_mask, dynamic_env_latent, output)
        return output

    def infer_scandots_latent(self, obs):
        scan = obs[:, self.num_prop : self.num_prop + self.num_scan]
        return self.scan_encoder(scan)


class ActorCriticRMA(nn.Module):
    is_recurrent = False

    def __init__(
        self,
        num_prop,
        num_scan,
        num_critic_obs,
        num_priv_latent,
        num_priv_explicit,
        num_hist,
        num_actions,
        num_dynamic_env_latent=0,
        dynamic_env_latent_cfg=None,
        scan_encoder_dims=[256, 256, 256],
        actor_hidden_dims=[256, 256, 256],
        critic_hidden_dims=[256, 256, 256],
        activation="elu",
        init_noise_std=1.0,
        **kwargs,
    ):
        if kwargs:
            print(
                "ActorCritic.__init__ got unexpected arguments, which will be ignored: "
                + str([key for key in kwargs.keys()])
            )
        super(ActorCriticRMA, self).__init__()

        self.kwargs = kwargs
        priv_encoder_dims = kwargs["priv_encoder_dims"]
        activation = get_activation(activation)

        self.actor = Actor(
            num_prop,
            num_scan,
            num_actions,
            scan_encoder_dims,
            actor_hidden_dims,
            priv_encoder_dims,
            num_priv_latent,
            num_priv_explicit,
            num_hist,
            activation,
            tanh_encoder_output=kwargs["tanh_encoder_output"],
            num_dynamic_env_latent=num_dynamic_env_latent,
            dynamic_env_latent_cfg=dynamic_env_latent_cfg,
        )

        # Value function
        critic_layers = []
        critic_layers.append(nn.Linear(num_critic_obs, critic_hidden_dims[0]))
        critic_layers.append(activation)
        for l in range(len(critic_hidden_dims)):
            if l == len(critic_hidden_dims) - 1:
                critic_layers.append(nn.Linear(critic_hidden_dims[l], 1))
            else:
                critic_layers.append(
                    nn.Linear(critic_hidden_dims[l], critic_hidden_dims[l + 1])
                )
                critic_layers.append(activation)
        self.critic = nn.Sequential(*critic_layers)

        # Action noise
        self.std = nn.Parameter(init_noise_std * torch.ones(num_actions))
        self.distribution = None
        # disable args validation for speedup
        Normal.set_default_validate_args = False

        # seems that we get better performance without init
        # self.init_memory_weights(self.memory_a, 0.001, 0.)
        # self.init_memory_weights(self.memory_c, 0.001, 0.)

    @staticmethod
    # not used at the moment
    def init_weights(sequential, scales):
        [
            torch.nn.init.orthogonal_(module.weight, gain=scales[idx])
            for idx, module in enumerate(
                mod for mod in sequential if isinstance(mod, nn.Linear)
            )
        ]

    def reset(self, dones=None):
        pass

    def forward(self):
        raise NotImplementedError

    @property
    def action_mean(self):
        return self.distribution.mean

    @property
    def action_std(self):
        return self.distribution.stddev

    @property
    def entropy(self):
        return self.distribution.entropy().sum(dim=-1)

    def update_distribution(self, observations, hist_encoding):
        mean = self.actor(observations, hist_encoding)
        self.distribution = Normal(mean, mean * 0.0 + self.std)

    def act(self, observations, hist_encoding=False, **kwargs):
        self.update_distribution(observations, hist_encoding)
        return self.distribution.sample()

    def get_actions_log_prob(self, actions):
        return self.distribution.log_prob(actions).sum(dim=-1)

    def act_inference(
        self,
        observations,
        hist_encoding=False,
        eval=False,
        scandots_latent=None,
        dynamic_env_latent=None,
        **kwargs,
    ):
        if not eval:
            actions_mean = self.actor(
                observations,
                hist_encoding,
                eval,
                scandots_latent,
                dynamic_env_latent,
            )
            return actions_mean
        else:
            actions_mean, latent_hist, latent_priv = self.actor(
                observations, hist_encoding, eval=True
            )
            return actions_mean, latent_hist, latent_priv

    def evaluate(self, critic_observations, **kwargs):
        value = self.critic(critic_observations)
        return value

    def reset_std(self, std, num_actions, device):
        new_std = std * torch.ones(num_actions, device=device)
        self.std.data = new_std.data


def get_activation(act_name):
    if act_name == "elu":
        return nn.ELU()
    elif act_name == "selu":
        return nn.SELU()
    elif act_name == "relu":
        return nn.ReLU()
    elif act_name == "crelu":
        return nn.ReLU()
    elif act_name == "lrelu":
        return nn.LeakyReLU()
    elif act_name == "tanh":
        return nn.Tanh()
    elif act_name == "sigmoid":
        return nn.Sigmoid()
    else:
        print("invalid activation function!")
        return None
