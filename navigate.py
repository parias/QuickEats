from flask import Flask, render_template, url_for, session, redirect, request
from flask_pymongo import PyMongo

app = Flask(__name__)
app.secret_key = 'helloworld'
