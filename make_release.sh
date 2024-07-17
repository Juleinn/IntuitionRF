# script to make a release archive of the plugin
# this is basic enough that we don't need any kind of CI here

version="$(python3 __init__.py --version)"
rm -rf /tmp/IntuitionRF/
cp -r "$(pwd)" /tmp/IntuitionRF
# delete everything we don't need in the release package
rm -rf /tmp/IntuitionRF/README.md
rm -rf /tmp/IntuitionRF/__pycache__/
rm -rf /tmp/IntuitionRF/operators/__pycache__/
rm -rf /tmp/IntuitionRF/panels/__pycache__/
rm -rf /tmp/IntuitionRF/images
rm -rf /tmp/IntuitionRF/*blend
rm -rf /tmp/IntuitionRF/*blend1
rm -rf /tmp/IntuitionRF/.git
rm -rf /tmp/IntuitionRF*.zir

# delete self
rm -rf /tmp/IntuitionRF/make_release.sh

cd /tmp
zip -r "IntuitionRF-$version-alpha.zip" IntuitionRF/*
