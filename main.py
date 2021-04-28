from flask import Flask, render_template, request, url_for, redirect, send_file
import logging
import json
import boto3
from botocore.exceptions import ClientError

app = Flask(__name__)

username_login = ''
userid_login = ''

def create_bucket(bucket_name, region=None):

    # Create bucket
    try:
        if region is None:
            s3_client = boto3.client('s3')
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client = boto3.client('s3', region_name=region)
            location = {'LocationConstraint': region}
            s3_client.create_bucket(Bucket=bucket_name,
                                    CreateBucketConfiguration=location)
    except ClientError as e:
        logging.error(e)
        return False
    return True


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


@app.route("/create")
def creation():
    error_msg = None
    try:
        dynamotable = create_music_table()
        print("Table status:", dynamotable.table_status)
    except Exception as e:
        error_msg = e
        return render_template('login.html', error_msg=error_msg)

@app.route("/")
def root():
    return render_template("login.html")


@app.route('/login', methods=["POST", "GET"])
def login():

    if request.method == "POST":
        user_id = request.form.get("user_id")
        password = request.form.get("password")
        error_msg = None

        try: 
                
            return render_template('login.html', error_msg=error_msg)

        except Exception as e:
            error_msg = e
        return render_template('login.html', error_msg=error_msg)
    else:
        return render_template('login.html')
        
@app.route('/register', methods=["POST", "GET"])
def register():

    if request.method == "POST":
        user_id = request.form.get("user_id")
        user_name = request.form.get("user_name")
        password = request.form.get("password")
        error_msg = None
        file_img = request.files['file']

        try:
            
            if 'file' not in request.files:
                error_msg = 'No file error'
                return render_template('register.html', error_msg=error_msg)

            if file_img.filename == '':
                error_msg = 'Please choose a file to upload as user avatar.'
                return render_template('register.html', error_msg=error_msg)


            else:
                
                return redirect(url_for("login"))

        except Exception as e:
            error_msg = e
        return render_template('register.html', error_msg=error_msg)

    else:
        return render_template('register.html')

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)

