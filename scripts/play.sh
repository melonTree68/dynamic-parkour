cd legged_gym/legged_gym/scripts
source ~/extreme-parkour/scripts/rc.sh

# play base policy
python play.py --delay --web --task a1_dynamic --proj_name original-pipeline-dynamic-terrain --exptid base --checkpoint 15000
python play.py --delay --record_video --task a1_dynamic --proj_name original-pipeline-dynamic-terrain --exptid base
python play.py --delay --record_video --video_width 320 --video_height 180 --task a1_dynamic --proj_name original-pipeline-dynamic-terrain --exptid base

# play distillation policy
python play.py --delay --use_camera --web --task a1_dynamic --proj_name original-pipeline-dynamic-terrain --exptid distill-from-15k --checkpoint 10000
python play.py --delay --use_camera --record_video --task a1_dynamic --proj_name original-pipeline-dynamic-terrain --exptid distill-from-15k
python play.py --delay --use_camera --record_video --video_width 320 --video_height 180 --task a1_dynamic --proj_name original-pipeline-dynamic-terrain --exptid distill-from-15k
