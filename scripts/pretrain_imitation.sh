cd legged_gym/legged_gym/scripts
source ~/extreme-parkour/scripts/rc.sh

# imitation pretrain policy
python pretrain_imitation.py --no_wandb --task a1_dynamic --expert_checkpoint 15000 --proj_name imitation-pretrain-dynamic-terrain --exptid imitate-base-15k-v2-91bf8ce

# fine-tune imitation-pretrained policy with base RL
python train.py --no_wandb --headless --resume --resumeid imitate-base-15k-v2-91bf8ce --checkpoint 100 --task a1_dynamic --proj_name imitation-pretrain-dynamic-terrain --exptid resume-from-imitate-base-15k-100-v2-91bf8ce
