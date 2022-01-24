# TG-Fullstack-Experiment

**Demo of tg cloud full stack**

1. Clone the repo
   `git clone <repo_url>`

2. navigate to front directory and install node_modules
   `cd front`
   `npm i`

3. Run the front end code
   `npm start`

4. Navigate to middleware directory and run the python virtual enviroment
   `cd ../middleware`
   `source venv/bin/activate`

5. Create a TigerGraph Cloud Solution and make the credential python file contains HOST, USERNAME, PASSWORD, and GRAPHNAME

6. Install the libraries and run the middleware
   `pip3 install -r requirements.txt`
   `uvicorn main:app --reload`
