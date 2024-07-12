# auto-restart blender on crash with the dev/example file

while true; do
    (
        sleep 0.2
        bspc node @parent -R 270
    ) &
    /home/anton/Downloads/blender-4.1.1-linux-x64/blender ./example.blend
done
