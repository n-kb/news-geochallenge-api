from flask import Flask
from flask import jsonify
from flask import request
from flask_pymongo import PyMongo
from flask_cors import CORS
from bson.objectid import ObjectId
import os
import utils

app = Flask(__name__)

port = int(os.environ.get('PORT', 5003))

if (os.environ.get('MONGODB_URI')):
	mongo_uri = os.environ.get('MONGODB_URI')
	app.config['MONGO_DBNAME'] = mongo_uri.split("/")[1]
	app.config['MONGO_URI'] = mongo_uri
else:
	app.config['MONGO_DBNAME'] = 'geochallenge'
	app.config['MONGO_URI'] = 'mongodb://localhost:27017/geochallenge'

cors = CORS(app)

mongo = PyMongo(app)

@app.route('/get_questions/<difficulty>', methods=['GET'])
def get_questions(difficulty):
  return utils.get_questions(mongo.db, difficulty)

@app.route('/get_scores', methods=['GET'])
def get_scores():
  return utils.get_scores(mongo.db)

@app.route('/send_score', methods=['POST'])
def add_score():
  return utils.add_score(mongo.db, request.json['points'], request.json['token'])

@app.route('/send_username', methods=['POST'])
def change_username():
  return utils.change_username(mongo.db, request.json['score_id'], request.json['username'])

if __name__ == '__main__':
    app.run(debug=True, port=port)