# Developer Quickstart
Developing/building only works on a Linux machine. 

First, clone the repository:
```
git clone https://github.com/TheVanadium/farm-ng-amiga-autonomous-navigation.git
```

## App
The app lives in the directory `amiga-app`
```
cd amiga-app
```

#### Frontend
```
cd ts
npm install
npm run dev
```
The `.env` file must have the VITE_API_URL constant configured to the backend port. Note that the Amiga screen's is 1280x800.

#### Backend
The backend only works on an Amiga device, requiring SSH access. To obtain it, follow the instructions at https://amiga.farm-ng.com/docs/ssh/.
```
python3 -m venv venv
source venv/Scripts/activate

pip install farm_ng_amiga-2.3.4-py3-none-any.whl
pip install -r requirements.txt

cd backend
python3 main.py
```

### Building the App on the Amiga
1. Create a manifest file (https://amiga.farm-ng.com/docs/brain/brain-apps-manifest/)
2. Configure the `.env` file to the manifest file's `app_route` value
3. Build the application: `./build.sh`
4. Install on Amiga: `./install.sh`
