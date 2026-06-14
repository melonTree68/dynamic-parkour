cd legged_gym/legged_gym/scripts
source ~/extreme-parkour/scripts/rc.sh

# train base policy
python train.py --no_wandb --headless --task a1_dynamic --proj_name original-pipeline-dynamic-terrain --exptid base
python train.py --no_wandb --headless --resume --resumeid base-expert --checkpoint 15000 --task a1_dynamic --proj_name imitation-pretrain-dynamic-terrain --exptid resume-from-base-15k

# train distillation policy
# a1 dynamic
python train.py --no_wandb --delay --use_camera --resume --resumeid resume-from-imitate-base-15k-100 --checkpoint 20000 --task a1_dynamic --proj_name augment-latent-roa-dynamic-terrain --exptid distill-from-resume-from-imitate-base-15k-100-20k
# a1 mixed
python train.py --no_wandb --delay --use_camera --resume --resumeid resume-from-imitate-base-15k-100 --checkpoint 20000 --task a1_mixed --proj_name augment-latent-hybrid-mixed-terrain --exptid distill-from-resume-from-imitate-base-15k-100-20k
