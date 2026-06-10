import types

import torch
import torch.nn as nn

from rsl_rl.modules.actor_critic import Actor
from rsl_rl.modules.depth_backbone import RecurrentDepthBackbone
from rsl_rl.runners.on_policy_runner import OnPolicyRunner


def make_actor(num_dynamic_env_latent=30):
    return Actor(
        num_prop=6,
        num_scan=4,
        num_actions=3,
        scan_encoder_dims=[8, 4],
        actor_hidden_dims=[16, 8],
        priv_encoder_dims=[5],
        num_priv_latent=3,
        num_priv_explicit=2,
        num_hist=10,
        activation=nn.ELU(),
        num_dynamic_env_latent=num_dynamic_env_latent,
        dynamic_env_latent_cfg=types.SimpleNamespace(
            recovery_modes={
                "hurdle": "roa",
                "gap": "teacher_student",
                "step": "roa",
                "tilted_pad": "teacher_student",
            }
        ),
    )


def make_obs(actor, batch_size=2):
    obs_dim = (
        actor.num_prop
        + actor.num_scan
        + actor.num_priv_explicit
        + actor.num_priv_latent
        + actor.num_dynamic_env_latent
        + actor.num_hist * actor.num_prop
    )
    obs = torch.randn(batch_size, obs_dim)
    if actor.num_dynamic_env_latent:
        start = actor._dynamic_env_start()
        labels = torch.zeros(batch_size, 2, 15)
        labels[:, 0, 0] = 1.0
        labels[:, 0, 1] = 1.0  # hurdle -> ROA
        labels[:, 1, 0] = 1.0
        labels[:, 1, 2] = 1.0  # gap -> teacher-student
        obs[:, start : start + actor.num_dynamic_env_latent] = labels.view(
            batch_size, -1
        )
    return obs


def test_actor_forward_supports_zero_and_dynamic_env_latent_dims():
    for dim in (0, 30):
        actor = make_actor(num_dynamic_env_latent=dim)
        obs = make_obs(actor)
        actions = actor(obs, hist_encoding=False)
        hist_actions = actor(obs, hist_encoding=True)
        assert actions.shape == (2, 3)
        assert hist_actions.shape == (2, 3)


def test_actor_dynamic_env_recovery_masks_are_family_specific():
    actor = make_actor(num_dynamic_env_latent=30)
    obs = make_obs(actor)
    roa_mask = actor.dynamic_env_recovery_mask(obs, "roa")
    ts_mask = actor.dynamic_env_recovery_mask(obs, "teacher_student")
    assert roa_mask.shape == (2, 30)
    assert ts_mask.shape == (2, 30)
    assert roa_mask[:, :15].all()
    assert not roa_mask[:, 15:].any()
    assert not ts_mask[:, :15].any()
    assert ts_mask[:, 15:].all()


class DummyDepthBackbone(nn.Module):
    def forward(self, images):
        return torch.zeros(images.shape[0], 32, device=images.device)


def test_recurrent_depth_backbone_outputs_scan_dynamic_and_yaw():
    cfg = types.SimpleNamespace(
        env=types.SimpleNamespace(n_proprio=6, n_dynamic_env_latent=30)
    )
    encoder = RecurrentDepthBackbone(DummyDepthBackbone(), cfg, scan_output_dim=32)
    output = encoder(torch.zeros(4, 58, 87), torch.zeros(4, 6))
    assert output.shape == (4, 32 + 30 + 2)


def test_compatible_loader_zero_initializes_expanded_weight_columns():
    runner = OnPolicyRunner.__new__(OnPolicyRunner)
    module = nn.Linear(5, 3)
    old_state = {
        "weight": torch.ones(3, 2),
        "bias": torch.arange(3, dtype=torch.float32),
    }
    runner._load_module_state_compatible(module, old_state, "linear")
    assert torch.equal(module.weight[:, :2], torch.ones(3, 2))
    assert torch.equal(module.weight[:, 2:], torch.zeros(3, 3))
    assert torch.equal(module.bias, old_state["bias"])


def test_compatible_loader_preserves_depth_yaw_rows_when_output_expands():
    class DummyExpandedDepth(nn.Module):
        def __init__(self):
            super().__init__()
            self.dynamic_output_dim = 2
            self.output_mlp = nn.Sequential(nn.Linear(4, 6))

    runner = OnPolicyRunner.__new__(OnPolicyRunner)
    module = DummyExpandedDepth()
    old_weight = torch.arange(16, dtype=torch.float32).view(4, 4)
    old_bias = torch.arange(4, dtype=torch.float32)
    runner._load_module_state_compatible(
        module,
        {"output_mlp.0.weight": old_weight, "output_mlp.0.bias": old_bias},
        "depth",
    )
    assert torch.equal(module.output_mlp[0].weight[:2], old_weight[:2])
    assert torch.equal(module.output_mlp[0].weight[2:4], torch.zeros(2, 4))
    assert torch.equal(module.output_mlp[0].weight[-2:], old_weight[-2:])
    assert torch.equal(module.output_mlp[0].bias[:2], old_bias[:2])
    assert torch.equal(module.output_mlp[0].bias[2:4], torch.zeros(2))
    assert torch.equal(module.output_mlp[0].bias[-2:], old_bias[-2:])
