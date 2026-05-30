from legged_gym.scripts.pretrain_imitation import (
    ImitationReplayBuffer,
    SOURCE_STUDENT,
    SOURCE_TEACHER,
)

import torch


def test_replay_buffer_keeps_capacity_per_source():
    buffer = ImitationReplayBuffer(capacity_per_source=3)
    obs = torch.arange(20, dtype=torch.float32).view(5, 4)
    actions = torch.arange(10, dtype=torch.float32).view(5, 2)

    buffer.add(SOURCE_TEACHER, obs, actions)

    assert buffer.size(SOURCE_TEACHER) == 3
    assert torch.equal(buffer._storage[SOURCE_TEACHER]["obs"], obs[-3:])
    assert torch.equal(buffer._storage[SOURCE_TEACHER]["actions"], actions[-3:])


def test_replay_buffer_samples_balanced_teacher_and_student():
    buffer = ImitationReplayBuffer(capacity_per_source=20)
    obs = torch.randn(10, 4)
    actions = torch.randn(10, 2)
    buffer.add(SOURCE_TEACHER, obs, actions)
    buffer.add(SOURCE_STUDENT, obs + 10.0, actions + 10.0)

    batch_obs, batch_actions, teacher_count, student_count = buffer.sample_balanced(
        batch_size=8, device="cpu"
    )

    assert batch_obs.shape == (8, 4)
    assert batch_actions.shape == (8, 2)
    assert teacher_count == 4
    assert student_count == 4


def test_replay_buffer_samples_single_source_before_dagger():
    buffer = ImitationReplayBuffer(capacity_per_source=20)
    obs = torch.randn(10, 4)
    actions = torch.randn(10, 2)
    buffer.add(SOURCE_TEACHER, obs, actions)

    batch_obs, batch_actions, teacher_count, student_count = buffer.sample_balanced(
        batch_size=6, device="cpu"
    )

    assert batch_obs.shape == (6, 4)
    assert batch_actions.shape == (6, 2)
    assert teacher_count == 6
    assert student_count == 0
