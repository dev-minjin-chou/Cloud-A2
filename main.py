from flask import Flask, render_template, request, url_for, redirect, send_file
from decimal import Decimal
import logging
import json
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr


app = Flask(__name__)

username_login = ''
email_login = ''


def upload_file(file_name, bucket, object_name=None):

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = file_name
        # Upload the file
        s3_client = boto3.client('s3')
    try:
        response = s3_client.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True


# Creating dynamodb table
def create_music_table(dynamodb=None):

    dynamodb = boto3.resource('dynamodb')

    table = dynamodb.create_table(
        TableName='music',
        KeySchema=[
             {
                'AttributeName': 'artist',
                'KeyType': 'HASH' 
            },
            {
                'AttributeName': 'title',
                'KeyType': 'RANGE'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'artist',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'title',
                'AttributeType': 'S'
            }

        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 10,
            'WriteCapacityUnits': 10
        }
    )
    return table


def load_data(musics, dynamodb=None):
    dynamodb = boto3.resource('dynamodb')

    table = dynamodb.Table('music')
    

    for music in musics['songs']:
        artist = music['artist']
        title = music['title']
        year = music['year']
        web_url = music['web_url']
        img_url = music['img_url']
        table.put_item(Item=music)
    
    return True
   
@app.route("/create")
def creation():
    error_msg = None
    try:
        dynamotable = create_music_table()
        if dynamotable is None:
            return render_template('create.html')
        else: 
            error_msg = 'Table has already been created..'
            return render_template('login.html', error_msg=error_msg)
    except Exception as e:
        error_msg = e
        return render_template('login.html', error_msg=error_msg)

# Loading data from a2.json to dynamo
@app.route("/load")
def load():
    error_msg = None
    try:
        with open('a2.json') as json_file:
            music_list = json.load(json_file, parse_float=Decimal)
        test = load_data(music_list)

        if test:
            return render_template('load.html')
        else:
            error_msg = 'Unable to add data'
            return render_template('login.html', error_msg=error_msg)
    except Exception as e:
        error_msg = e
        logging.error(e)
        return render_template('login.html', error_msg=error_msg)


@app.route("/")
def root():
    return render_template("login.html")

# Querying dynamo by email.
def query(email, dynamodb=None):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('login')

    response = table.query(
        KeyConditionExpression=Key('email').eq(email),
    )
    return response['Items']

@app.route('/login', methods=["POST", "GET"])
def login():

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        error_msg = None

        try: 
            query_result = query(email)
            if len(query_result) > 0:
                if email != query_result[0]['email']:
                    error_msg = 'Email or password is invalid'
                    return render_template('login.html', error_msg=error_msg)
                elif password != query_result[0]['password']:
                    error_msg = 'Email or password is invalid'
                    return render_template('login.html', error_msg=error_msg)
                else:
                    return render_template('main.html', error_msg=error_msg)
            else:
                error_msg = 'Email or password is invalid'
                return render_template('login.html', error_msg=error_msg)

        except Exception as e:
            error_msg = e
        return render_template('login.html', error_msg=error_msg)
    else:
        return render_template('login.html')
        

# For creating new user
def put_user(email, username, password, dynamodb=None):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('login')
    response = table.put_item(
        Item={
            'email': email,
            'user_name': username,
            'password': password
        }
    )
    return True

@app.route('/register', methods=["POST", "GET"])
def register():

    if request.method == "POST":
        email = request.form.get("email")
        user_name = request.form.get("user_name")
        password = request.form.get("password")
        error_msg = None

        try:
            query_result = query(email)
            if len(query_result) > 0:
                if email == query_result[0]['email']:
                    error_msg = 'The email already exists.'
                    return render_template('register.html', error_msg=error_msg)

            else:
                addUser = put_user(email, user_name, password)

                if addUser:
                    return redirect(url_for("login"))
                else:
                    error_msg = 'Failed to create an account..'
                    return render_template('register.html', error_msg=error_msg)

        except Exception as e:
            error_msg = e
        return render_template('register.html', error_msg=error_msg)

    else:
        return render_template('register.html')


@app.route('/main', methods=["POST", "GET"])
def main():
     
    return render_template('main.html')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)

