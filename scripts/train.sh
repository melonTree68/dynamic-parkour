cd legged_gym/legged_gym/scripts
source ~/extreme-parkour/scripts/rc.sh

# train base policy
python train.py --no_wandb --headless --task a1_dynamic --proj_name original-pipeline-dynamic-terrain --exptid base

# train distillation policy
python train.py --no_wandb --delay --use_camera --resume --resumeid base --checkpoint 15000 --task a1_dynamic --proj_name original-pipeline-dynamic-terrain --exptid distill-from-15k
