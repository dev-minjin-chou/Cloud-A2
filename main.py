from flask import Flask, render_template, request, url_for, redirect, send_file
from decimal import Decimal
import logging
import json
import boto3
import requests
import os
import tempfile
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr


app = Flask(__name__)

username_login = ''
email_login = ''


# Uploading img to s3
def upload_file(file_name, bucket, object_name=None):

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = file_name

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

# Download images based on url.
def download_img(img_url, filename):
    resource = requests.get(img_url)
    file = open(filename, "wb")
    file.write(resource.content)
    file.close()

# Auto creates table
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

# Uploading image to bucket
@app.route("/bucket")
def upload_s3():
    error_msg = None
    try:
        with open('a2.json') as json_file:
            music_list = json.load(json_file, parse_float=Decimal)
            for music in music_list['songs']:
                img_url = music['img_url']
                file_path = '/tmp/' + img_url.split("/")[-1]
                test = download_img(img_url, file_path)
                object_name = img_url.split("/")[-1]
                upload_file(file_path, 'cloudcomputingaassignment2', object_name)

            return render_template('bucket.html')    

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
            query_result1 = query(email)
            if len(query_result1) > 0:
                if email != query_result1[0]['email']:
                    error_msg = 'Email or password is invalid'
                    return render_template('login.html', error_msg=error_msg)
                elif password != query_result1[0]['password']:
                    error_msg = 'Email or password is invalid'
                    return render_template('login.html', error_msg=error_msg)
                else:
                    global username_login, email_login
                    email_login = query_result1[0]['email']
                    username_login = query_result1[0]['user_name']
                    subscriptions = get_musics(username_login)
                    return render_template('main.html', error_msg=error_msg, username_login=username_login, subscriptions=subscriptions)
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

# For user to subscribe a music
@app.route('/subscribe')
def subscribe(dynamodb=None):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('subscription')

    artist = request.args.get('artist')
    title = request.args.get('title')
    img_url = request.args.get('img_url')
    web_url = request.args.get('web_url')
    year = request.args.get('year')
    user_name = request.args.get('user_name')


    response = table.put_item(Item={
        'user_name': user_name,
        'artist': artist,
        'title': title,
        'img_url': img_url,
        'web_url': web_url,
        'year': year
    })
    return render_template('subscribe.html')


# Display user subscribed musics
def get_musics(user_name, dynamodb=None):
    dynamodb =  boto3.resource('dynamodb')
    table = dynamodb.Table('subscription')

    response = table.query(
        KeyConditionExpression=Key('user_name').eq(user_name)
    )
    return response['Items']


# Delete music from dynamo when user click remove.
@app.route('/remove')
def remove(dynamodb=None):
    dynamodb =  boto3.resource('dynamodb')
    table = dynamodb.Table('subscription')
    user_name = request.args.get('user_name')
    artist = request.args.get('artist')

    response = table.delete_item(
        Key={
            'user_name': user_name,
            'artist': artist
        }
    )   
    return render_template('remove.html')


def query_table(artist, title, year, dynamodb=None):
    dynamodb =  boto3.resource('dynamodb')
    table = dynamodb.Table('music')

    if artist == '':
        if title == '':
            if year != '':
                response = table.scan(
                    FilterExpression=Attr('year').eq(year)
                )
                return response['Items']
    if artist != '':
        if title == '' and year == '':
            response = table.query(
                KeyConditionExpression=Key('artist').eq(artist)
            )
            return response['Items']
    if artist == '' and year == '':
        if title != '':
            response = table.scan(
                FilterExpression=Attr('title').eq(title)
            )
            return response['Items']
    if artist != '':
        if title != '' and year == '':
            response = table.query(
                KeyConditionExpression=Key('artist').eq(artist) & Key('title').eq(title)
            )
            return response['Items']
    if artist != '':
        if title == '' and year != '':
            response = table.query(
                KeyConditionExpression=Key('artist').eq(artist),
                FilterExpression=Attr('year').eq(year)
            )
            return response['Items']
    if artist == '':
        if title != '' and year != '':
            response = table.scan(
                FilterExpression=Attr('year').eq(year) & Attr('title').eq(title)
            )
            return response['Items']
    if artist != '':
        if title != '' and year != '':
            response = table.query(
                KeyConditionExpression=Key('artist').eq(artist) & Key('title').eq(title),
                FilterExpression=Attr('year').eq(year)
            )
            return response['Items']

@app.route('/main', methods=["POST", "GET"])
def main():
    userName = username_login
    try:
        query_username = query(email_login)
    except Exception as e:
        error_msg = 'Timed-out. Please re-login to continue session.'
        return render_template('login.html', error_msg=error_msg)

    if userName == query_username[0]['user_name']:
        newUsername = userName
    subscriptions = get_musics(newUsername)

    if request.method == "POST":
        try:
            title = request.form.get("title")
            year = request.form.get("year")
            artist = request.form.get("artist")
            error_msg = None
            query_result = query_table(artist, title, year)

            if query_result is not None:
                if len(query_result) > 0:
                    return render_template('main.html', newUsername=username_login, query_result=query_result,subscriptions=subscriptions, error_msg=error_msg)
                else:
                    error_msg = 'No result is  retrieved. Please query again.'
                    return render_template('main.html', newUsername=username_login, subscriptions=subscriptions, error_msg=error_msg)
            else:
                error_msg = 'No result is  retrieved. Please query again.'
                return render_template('main.html', newUsername=username_login, subscriptions=subscriptions, error_msg=error_msg)
           
        except Exception as e:
            error_msg = e
            return render_template('main.html', newUsername=username_login, subscriptions=subscriptions, error_msg=error_msg)
    else:
        return render_template('main.html', newUsername=username_login, subscriptions=subscriptions)



if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)

