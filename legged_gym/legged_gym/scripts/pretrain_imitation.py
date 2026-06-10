# SPDX-FileCopyrightText: Copyright (c) 2021 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause

import csv
import os
import statistics
import time


SOURCE_TEACHER = "teacher"
SOURCE_STUDENT = "student"
CSV_HEADER = [
    "checkpoint",
    "action_loss",
    "hist_action_loss",
    "estimator_loss",
    "dynamic_env_roa_loss",
    "total_loss",
    "teacher_buffer_size",
    "student_buffer_size",
    "teacher_samples",
    "student_samples",
]

torch = None
F = None
wandb = None
LEGGED_GYM_ROOT_DIR = None
get_args = None
get_load_path = None
task_registry = None


def _get_torch():
    global torch
    if torch is None:
        import torch as torch_module

        torch = torch_module
    return torch


def _load_runtime_modules():
    global F, LEGGED_GYM_ROOT_DIR, get_args, get_load_path, task_registry, torch, wandb
    if F is not None:
        return

    import isaacgym  # noqa: F401
    import torch as torch_module
    import torch.nn.functional as functional
    import wandb as wandb_module
    import legged_gym.envs  # noqa: F401 - registers tasks.
    from legged_gym import LEGGED_GYM_ROOT_DIR as root_dir
    from legged_gym.utils import (
        get_args as args_fn,
        get_load_path as load_path_fn,
        task_registry as registry,
    )

    # Keep the module global so helpers and tests use one torch handle.
    torch = torch_module
    F = functional
    wandb = wandb_module
    LEGGED_GYM_ROOT_DIR = root_dir
    get_args = args_fn
    get_load_path = load_path_fn
    task_registry = registry


class ImitationReplayBuffer:
    def __init__(self, capacity_per_source):
        if capacity_per_source <= 0:
            raise ValueError("capacity_per_source must be positive.")
        self.capacity_per_source = int(capacity_per_source)
        self._storage = {
            SOURCE_TEACHER: {"obs": None, "actions": None},
            SOURCE_STUDENT: {"obs": None, "actions": None},
        }

    def add(self, source, obs, actions):
        torch_module = _get_torch()
        if source not in self._storage:
            raise ValueError(f"Unknown replay source: {source}")
        if obs.shape[0] != actions.shape[0]:
            raise ValueError("obs and actions must have the same batch dimension.")

        obs = obs.detach().cpu()
        actions = actions.detach().cpu()
        partition = self._storage[source]
        if partition["obs"] is None:
            partition["obs"] = obs
            partition["actions"] = actions
        else:
            partition["obs"] = torch_module.cat((partition["obs"], obs), dim=0)
            partition["actions"] = torch_module.cat(
                (partition["actions"], actions), dim=0
            )

        overflow = self.size(source) - self.capacity_per_source
        if overflow > 0:
            partition["obs"] = partition["obs"][overflow:]
            partition["actions"] = partition["actions"][overflow:]

    def size(self, source=None):
        if source is None:
            return self.size(SOURCE_TEACHER) + self.size(SOURCE_STUDENT)
        partition = self._storage[source]
        if partition["obs"] is None:
            return 0
        return partition["obs"].shape[0]

    def sample_balanced(self, batch_size, device):
        if batch_size <= 0:
            raise ValueError("batch_size must be positive.")
        torch_module = _get_torch()
        teacher_size = self.size(SOURCE_TEACHER)
        student_size = self.size(SOURCE_STUDENT)
        if teacher_size + student_size == 0:
            raise RuntimeError("Cannot sample from an empty replay buffer.")

        if teacher_size == 0:
            teacher_count = 0
            student_count = batch_size
        elif student_size == 0:
            teacher_count = batch_size
            student_count = 0
        else:
            teacher_count = batch_size // 2
            student_count = batch_size - teacher_count

        obs_parts = []
        action_parts = []
        if teacher_count > 0:
            obs, actions = self._sample_source(SOURCE_TEACHER, teacher_count)
            obs_parts.append(obs)
            action_parts.append(actions)
        if student_count > 0:
            obs, actions = self._sample_source(SOURCE_STUDENT, student_count)
            obs_parts.append(obs)
            action_parts.append(actions)

        return (
            torch_module.cat(obs_parts, dim=0).to(device),
            torch_module.cat(action_parts, dim=0).to(device),
            teacher_count,
            student_count,
        )

    def _sample_source(self, source, count):
        torch_module = _get_torch()
        size = self.size(source)
        indices = torch_module.randint(size, (count,))
        partition = self._storage[source]
        return partition["obs"][indices], partition["actions"][indices]


def _make_log_dir(args):
    log_dir = os.path.join(LEGGED_GYM_ROOT_DIR, "logs", args.proj_name, args.exptid)
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def _resolve_expert_path(args):
    root = os.path.join(
        LEGGED_GYM_ROOT_DIR,
        "logs",
        args.expert_proj_name,
        args.expert_exptid,
    )
    return get_load_path(root, checkpoint=args.expert_checkpoint)


def _init_wandb(args):
    mode = "disabled" if args.no_wandb or args.debug else "online"
    wandb.init(
        project=args.proj_name,
        name=args.exptid,
        entity="parkour",
        group=args.exptid[:3] if args.exptid else None,
        mode=mode,
        dir="../../logs",
    )


def _configure_args(args):
    args.headless = True
    if args.student_init not in ("scratch", "expert"):
        raise ValueError("--student_init must be either 'scratch' or 'expert'.")
    if args.debug:
        args.rows = 2
        args.cols = 2
        args.num_envs = 64
        if args.max_iterations is None:
            args.max_iterations = 2
    return args


def _make_student_and_expert(args, env, log_dir):
    expert_path = _resolve_expert_path(args)
    expert_runner, _ = task_registry.make_alg_runner(
        log_root=None,
        env=env,
        name=args.expert_task,
        args=args,
        init_wandb=False,
    )
    expert_runner.load(expert_path, load_optimizer=False)
    expert_runner.alg.actor_critic.eval()
    expert_runner.alg.estimator.eval()
    for param in expert_runner.alg.actor_critic.parameters():
        param.requires_grad_(False)
    for param in expert_runner.alg.estimator.parameters():
        param.requires_grad_(False)

    student_runner, train_cfg = task_registry.make_alg_runner(
        log_root=log_dir,
        env=env,
        name=args.task,
        args=args,
        init_wandb=False,
    )
    if args.student_init == "expert":
        student_runner.load(expert_path, load_optimizer=False)

    return student_runner, expert_runner, train_cfg, expert_path


def _expert_actions(expert_runner, obs):
    with torch.no_grad():
        return expert_runner.alg.actor_critic.act_inference(
            obs.to(expert_runner.device), hist_encoding=True
        )


def _student_actions(student_runner, obs):
    with torch.no_grad():
        return student_runner.alg.actor_critic.act_inference(
            obs.to(student_runner.device), hist_encoding=True
        )


def _collect_rollout(
    env,
    obs,
    expert_runner,
    student_runner,
    replay_buffer,
    driver,
    source,
    num_steps,
):
    if driver not in ("expert", "student"):
        raise ValueError("driver must be 'expert' or 'student'.")

    rewards = []
    done_count = 0
    for _ in range(num_steps):
        expert_actions = _expert_actions(expert_runner, obs)
        replay_buffer.add(source, obs, expert_actions)

        if driver == "expert":
            actions = expert_actions
        else:
            actions = _student_actions(student_runner, obs)

        obs, _, reward, dones, _ = env.step(actions.detach().to(env.device))
        rewards.append(reward.detach().mean().item())
        done_count += int(dones.sum().item())

    return obs, {
        "reward_mean": statistics.mean(rewards) if rewards else 0.0,
        "done_count": done_count,
    }


def _dynamic_env_roa_loss(actor, obs_batch):
    if actor.num_dynamic_env_latent == 0:
        return obs_batch.new_tensor(0.0)
    mask = actor.dynamic_env_recovery_mask(obs_batch, "roa")
    if not torch.any(mask):
        return obs_batch.new_tensor(0.0)
    target = actor.infer_priv_dynamic_env_latent(obs_batch).detach()
    prediction = actor.infer_hist_dynamic_env_latent(obs_batch)
    diff = (prediction - target).pow(2) * mask.float()
    return diff.sum() / mask.float().sum().clamp(min=1.0)


def _train_imitation_epoch(student_runner, replay_buffer, train_cfg):
    num_prop = student_runner.env.cfg.env.n_proprio
    num_scan = student_runner.env.cfg.env.n_scan
    priv_dim = student_runner.alg.priv_states_dim
    batch_size = max(
        2,
        student_runner.env.num_envs
        * student_runner.num_steps_per_env
        // train_cfg.algorithm.num_mini_batches,
    )
    if (
        replay_buffer.size(SOURCE_TEACHER) > 0
        and replay_buffer.size(SOURCE_STUDENT) > 0
    ):
        batch_size = max(2, batch_size + batch_size % 2)

    sums = {
        "action_loss": 0.0,
        "hist_action_loss": 0.0,
        "estimator_loss": 0.0,
        "dynamic_env_roa_loss": 0.0,
        "total_loss": 0.0,
        "teacher_samples": 0,
        "student_samples": 0,
    }
    num_updates = (
        train_cfg.algorithm.num_learning_epochs * train_cfg.algorithm.num_mini_batches
    )

    student_runner.alg.actor_critic.train()
    student_runner.alg.estimator.train()
    for _ in range(num_updates):
        obs_batch, action_targets, teacher_count, student_count = (
            replay_buffer.sample_balanced(batch_size, student_runner.device)
        )
        action_pred = student_runner.alg.actor_critic.actor(
            obs_batch, hist_encoding=False
        )
        hist_action_pred = student_runner.alg.actor_critic.actor(
            obs_batch, hist_encoding=True
        )
        priv_target = obs_batch[:, num_prop + num_scan : num_prop + num_scan + priv_dim]
        priv_pred = student_runner.alg.estimator(obs_batch[:, :num_prop])

        action_loss = F.mse_loss(action_pred, action_targets)
        hist_action_loss = F.mse_loss(hist_action_pred, action_targets)
        estimator_loss = F.mse_loss(priv_pred, priv_target)
        dynamic_env_roa_loss = _dynamic_env_roa_loss(
            student_runner.alg.actor_critic.actor, obs_batch
        )
        total_loss = (
            action_loss
            + hist_action_loss
            + estimator_loss
            + student_runner.alg.dynamic_env_roa_loss_weight * dynamic_env_roa_loss
        )

        student_runner.alg.optimizer.zero_grad()
        student_runner.alg.estimator_optimizer.zero_grad()
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(
            student_runner.alg.actor_critic.actor.parameters(),
            student_runner.alg.max_grad_norm,
        )
        torch.nn.utils.clip_grad_norm_(
            student_runner.alg.estimator.parameters(),
            student_runner.alg.max_grad_norm,
        )
        student_runner.alg.optimizer.step()
        student_runner.alg.estimator_optimizer.step()

        sums["action_loss"] += action_loss.item()
        sums["hist_action_loss"] += hist_action_loss.item()
        sums["estimator_loss"] += estimator_loss.item()
        sums["dynamic_env_roa_loss"] += dynamic_env_roa_loss.item()
        sums["total_loss"] += total_loss.item()
        sums["teacher_samples"] += teacher_count
        sums["student_samples"] += student_count

    for key in (
        "action_loss",
        "hist_action_loss",
        "estimator_loss",
        "dynamic_env_roa_loss",
        "total_loss",
    ):
        sums[key] /= num_updates
    return sums


def _append_csv(log_dir, row):
    path = os.path.join(log_dir, "imitation_metrics.csv")
    write_header = not os.path.exists(path)
    with open(path, "a", newline="") as metrics_file:
        writer = csv.DictWriter(metrics_file, fieldnames=CSV_HEADER)
        if write_header:
            writer.writeheader()
        writer.writerow({key: row[key] for key in CSV_HEADER})


def _log_iteration(it, num_iterations, losses, replay_buffer, rollout_stats, log_dir):
    row = {
        "checkpoint": it,
        "action_loss": losses["action_loss"],
        "hist_action_loss": losses["hist_action_loss"],
        "estimator_loss": losses["estimator_loss"],
        "dynamic_env_roa_loss": losses["dynamic_env_roa_loss"],
        "total_loss": losses["total_loss"],
        "teacher_buffer_size": replay_buffer.size(SOURCE_TEACHER),
        "student_buffer_size": replay_buffer.size(SOURCE_STUDENT),
        "teacher_samples": losses["teacher_samples"],
        "student_samples": losses["student_samples"],
    }
    _append_csv(log_dir, row)
    wandb_row = dict(row)
    wandb_row["rollout_reward_mean"] = rollout_stats["reward_mean"]
    wandb_row["rollout_done_count"] = rollout_stats["done_count"]
    wandb.log(wandb_row, step=it)

    print(
        "Iteration {}/{} | action {:.6f} | hist {:.6f} | estimator {:.6f} | dynamic {:.6f} | "
        "buffers teacher={} student={} | rollout reward {:.3f} done_count={}".format(
            it,
            num_iterations,
            losses["action_loss"],
            losses["hist_action_loss"],
            losses["estimator_loss"],
            losses["dynamic_env_roa_loss"],
            replay_buffer.size(SOURCE_TEACHER),
            replay_buffer.size(SOURCE_STUDENT),
            rollout_stats["reward_mean"],
            rollout_stats["done_count"],
        )
    )


def pretrain(args):
    _load_runtime_modules()
    args = _configure_args(args)
    log_dir = _make_log_dir(args)
    _init_wandb(args)

    env, _ = task_registry.make_env(name=args.task, args=args)
    student_runner, expert_runner, train_cfg, expert_path = _make_student_and_expert(
        args, env, log_dir
    )
    print(f"Loaded expert checkpoint: {expert_path}")
    print(f"Student initialization: {args.student_init}")

    replay_buffer = ImitationReplayBuffer(args.replay_capacity)
    obs = env.get_observations()
    if args.max_iterations is not None:
        num_iterations = args.max_iterations
    else:
        num_iterations = args.imitation_iterations

    for it in range(num_iterations):
        start = time.time()
        if it < args.bc_iterations:
            obs, rollout_stats = _collect_rollout(
                env,
                obs,
                expert_runner,
                student_runner,
                replay_buffer,
                driver="expert",
                source=SOURCE_TEACHER,
                num_steps=student_runner.num_steps_per_env,
            )
        else:
            obs, teacher_stats = _collect_rollout(
                env,
                obs,
                expert_runner,
                student_runner,
                replay_buffer,
                driver="expert",
                source=SOURCE_TEACHER,
                num_steps=student_runner.num_steps_per_env,
            )
            obs, student_stats = _collect_rollout(
                env,
                obs,
                expert_runner,
                student_runner,
                replay_buffer,
                driver="student",
                source=SOURCE_STUDENT,
                num_steps=student_runner.num_steps_per_env,
            )
            rollout_stats = {
                "reward_mean": (
                    teacher_stats["reward_mean"] + student_stats["reward_mean"]
                )
                / 2.0,
                "done_count": teacher_stats["done_count"] + student_stats["done_count"],
            }

        losses = _train_imitation_epoch(student_runner, replay_buffer, train_cfg)
        student_runner.current_learning_iteration = it
        if it % args.imitation_save_interval == 0 or it == num_iterations - 1:
            student_runner.save(os.path.join(log_dir, f"model_{it}.pt"))

        _log_iteration(
            it, num_iterations, losses, replay_buffer, rollout_stats, log_dir
        )
        print(f"Iteration time: {time.time() - start:.2f}s")

    student_runner.current_learning_iteration = num_iterations
    student_runner.save(os.path.join(log_dir, f"model_{num_iterations}.pt"))


if __name__ == "__main__":
    _load_runtime_modules()
    pretrain(get_args())
