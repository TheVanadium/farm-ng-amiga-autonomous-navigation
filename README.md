# Robot Herb Estimation Project

We're programming the [farm-ng Amiga](https://farm-ng.com/amiga/) to estimate herb harvest yields using [ToF cameras](https://shop.luxonis.com/products/oak-d-sr-poe?variant=46456301027551). [Preliminary experiments](https://thevanadium.github.io/portfolio/2024-08-Fall-CSE-302-poster.pdf) show our system is promising. If you'd like to contribute, check out [CONTRIBUTING.md](https://github.com/TheVanadium/farm-ng-amiga-autonomous-navigation/blob/master/CONTRIBUTING.md).

## The Code

We have code that does a number of things necessary for herb yield estimation. For more detail, check out their respective READMEs.



## Our Collaborators
A big thanks to the people and organizations we've collaborated with:
- [farm-ng](https://farm-ng.com/)
- [Innovate To Grow](https://i2g.ucmerced.edu/)
- [SupHerb Farms](https://supherbfarms.com/)
- [UC Merced Environmental Smart Farm](https://vista.ucmerced.edu/farm/)


## Developer Quickstart
Developing/building only works on a Linux machine. 

First, clone the repository:
```bash
git clone https://github.com/TheVanadium/farm-ng-amiga-autonomous-navigation.git
```

#### Frontend
```bash
cd ts
npm install
npm run dev
```
The `.env` file must have the VITE_API_URL constant configured to the backend port. Note that the Amiga screen's is 1280x800.

#### Backend
To run the backend, you must first create a manifest file (https://amiga.farm-ng.com/docs/brain/brain-apps-manifest/).

The complete backend only works on an Amiga device, requiring SSH access. To obtain it, follow the instructions at https://amiga.farm-ng.com/docs/ssh/. 

```bash
python3 -m venv venv
source venv/Scripts/activate

pip install farm_ng_amiga-2.3.4-py3-none-any.whl
pip install -r requirements.txt

cd backend
python3 main.py
```

### Building the App on the Amiga
1. Configure the `.env` file to the manifest file's `app_route` value
2. Build and install the application: `./build.sh`
3. Install on Amiga: `./install.sh`


### `multi-cam-calibration/`
Code that calibrates the cameras for point cloud combination. TODO: integrate this into the actual app.
