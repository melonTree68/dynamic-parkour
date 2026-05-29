cd legged_gym/legged_gym/scripts
source ~/extreme-parkour/scripts/rc.sh

# evaluate base policy
python evaluate.py --delay --task a1_dynamic --proj_name original-pipeline-dynamic-terrain --exptid base --checkpoint 15000

# evaluate distillation policy
python evaluate.py --delay --use_camera --task a1_dynamic --proj_name original-pipeline-dynamic-terrain --exptid distill-from-15k --checkpoint 10000
