# NM-Api

Rest API wrapper for the official N&M Games API, adding support for authentication, reactions and about me.

## Setup
Install dependencies by running: `pip install -r requirements.txt`

Set the following environment variables:
- db: the MongoDB connection URL
- secret: secret for generating JWT tokens

## Running

You can run the project with `uvicorn main:app --reload`
