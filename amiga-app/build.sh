#!/bin/bash -x

# create virtual environment for the backend
python3 -m venv venv
source venv/bin/activate

# install dependencies
pip install -r requirements.txt

# build the frontend
cd ts/
sudo apt update
sudo apt install curl
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.4/install.sh | bash
nvm install 18
npm install
npm run build