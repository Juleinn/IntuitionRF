# IntuitionRF
IntuitionRF is an OpenEMS wrapper plugin for blender aiming to make dealing with RF simulation more intuitive. 

OpenEMS project page : https://www.openems.de/

## Contents
  - [Install](#install)
    - [Dependencies](#dependencies)
      - [1. Install OpenEMS](#1-install-openems)
      - [2. Install Additionnal python deps](#2-install-additionnal-python-deps)
      - [3. Install this plugin](#3-install-this-plugin)
      - [4. Enable the addon](#4-enable-the-addon)
      - [5. Reload plugins](#5-reload-plugins)
      - [6. Properties](#6-properties)


## Install 
### Dependencies
#### 1. Install OpenEMS 
IntuitionRF does not provide a OpenEMS distribution, you have to install a version yourself.

[Install Instructions for OpenEMS](https://docs.openems.de/install/index.html)

Requirements:
- OpenEMS must be built with python interface enabled 
- OpenEMS must be built against the same python version blender is using

#### 2. Install Additionnal python deps
Additional Python dependencies: 
```bash 
pip install vtk
pip install matplotlib
```
Once you have the python examples from OpenEMS running, 

#### 3. Install this plugin
Download this repo as ```.zip``` file then install as a regular addon

#### 4. Enable the addon
1. Enable the addon 

![enable the addon](images/preferences.png)

2. put your OpenEMS's python version syspath into this.

-  If you compiled OpenEMS against your system's python version, you can use the 'detect systen' to get the syspath automatically

- If you compiled OpenEMS against a virtualized environment (conda, venv, ...) then run the following in the python interpreter :
```python 
import sys 
print(sys.path)
```

then copy the output to the addon's configuration syspath

#### 5. Reload plugins

Use blender's 'reload scripts' (F3->reload scripts). The plugin should now be ready. If not, try restarting blender

![syspath](images/syspath.png)
![reload](images/reload_scripts.png)

#### 6. Properties
You should now see new IntuitionRF properties panels under the 'object' and 'scene' categories.
![panels](images/panels.png)

