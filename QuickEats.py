from flask import Flask, jsonify, render_template, url_for, request, session, redirect, flash
from collections import Counter, defaultdict
from datetime import datetime, date, time
from bson.objectid import ObjectId
from flask_pymongo import PyMongo
from OpenSSL import SSL
import pycard
import bcrypt
import time
import ast

app = Flask(__name__)
app.secret_key = 'helloworld'
app.config['TEMPLATES_AUTO_RELOAD'] = True 

app.config['MONGO_DBNAME'] = 'quickeats'
app.config['MONGO_URI'] = 'mongodb://localhost:27017/quickeats'

mongo = PyMongo(app)


@app.route('/')
def index():
    if 'username' in session:
        return render_template('home.html')
    return render_template('index.html')


@app.route('/login', methods=['POST'])
def login():
    users = mongo.db.users
    login_user = users.find_one({'username':request.form['username']})

    if login_user:
        if bcrypt.hashpw(request.form['pass'].encode('utf-8'), login_user['password']) == login_user['password']:
            session['username'] = request.form['username']
            session['user_type'] = mongo.db.users.find_one({'username':request.form['username']})['user_type']
            user_type = session['user_type']
            session['cart'] = []
            if user_type == 'chauffeur':
                mongo.db.users.update({'username':session['username']}, {"$set":{'on_clock':True}})
            return redirect(url_for('home'))
        return 'Invalid username/password combination'

    return 'Invalid username/password combination'


@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        users = mongo.db.users
        existing_user = users.find_one({'username':request.form['username']})

        if existing_user is None:
            hashpass = bcrypt.hashpw(request.form['pass'].encode('utf-8'), bcrypt.gensalt())

            # User Creation by user_type
            if request.form['user_type'] == 'patron':
                users.insert({
                    'username':request.form['username'], 
                    'password':hashpass, 
                    'address':request.form['address'], 
                    'city':request.form['city'], 
                    'state':request.form['state'],
                    'user_type':request.form['user_type']
                    })
            elif request.form['user_type'] == 'captain':
                users.insert({
                    'username':request.form['username'], 
                    'password':hashpass, 
                    'restaurant':request.form['restaurant'],
                    'user_type':request.form['user_type']
                    })
            elif request.form['user_type'] == 'buddy':
                users.insert({
                    'username':request.form['username'], 
                    'password':hashpass, 
                    'restaurant':request.form['restaurant'],
                    'user_type':request.form['user_type']
                    })
            elif request.form['user_type'] == 'chauffeur':
                users.insert({
                    'username':request.form['username'], 
                    'password':hashpass, 
                    'user_type':request.form['user_type'],
                    'on_clock':True
                    })
            elif request.form['user_type'] == 'nerd':
                users.insert({
                    'username':request.form['username'],
                    'password':hashpass,
                    'user_type':request.form['user_type']
                    })
            else: 
                users.insert({
                    'username':request.form['username'],
                    'password':hashpass,
                    'user_type':request.form['user_type']
                    })
            
            # Create Session variables when Registering
            session['username'] = request.form['username']
            session['user_type'] = request.form['user_type']
            session['cart'] = []
            return redirect(url_for('home'))

        return 'That username already exists!'

    return render_template('register.html')


@app.route('/home/')
def home(username=None):
    if 'username' in session:
        return render_template('home.html', username=session['username'])
    else:
        return redirect('/')


@app.route('/menu/')
def menu():
    menu = {}
    for item in mongo.db.menu.find():
        menu.update({
            item['entree']: {
                'description':item['description'],
                'cost': item['cost'], 
                'img': item['img'] 
            }
        })

    # If Buddy, then adds 'Add Menu Item' button 
    if 'user_type' in session:
        return render_template('menu.html',menu=menu, user_type=session['user_type'])
    else:
        return render_template('menu.html',menu=menu)


@app.route('/orders/')
def orders():
    if 'username' in session:
        user = mongo.db.users.find_one({'username':session['username']})

        # If Buddy, shows orders that need to be completed
        if user['user_type'] == 'buddy':
            orders = {}
            for item in mongo.db.orders.find({'restaurant':user['restaurant'], 'completed':False}):
                order_id = str(item['_id'])
                orders.update({
                    order_id: {
                        'entree':item['entree'],
                        'address':item['address'],
                        'cost':item['cost'],
                        'restaurant':item['restaurant'],
                        'completed':item['completed']
                    }
                })
                
            return render_template('orders.html',orders=orders, user_type=user['user_type'])

        # If Chauffeur, shows orders than need to be completed
        if user['user_type'] == 'chauffeur':
            orders = {}
            for item in mongo.db.orders.find({'completed':False, 'requested_delivery':True}):
                order_id = str(item['_id'])
                orders.update({
                    order_id: {
                        'entree':item['entree'],
                        'address':item['address'],
                        'cost':item['cost'],
                        'restaurant':item['restaurant'],
                        'completed':item['completed']
                    }
                })
                    
            return render_template('orders.html',orders=orders, user_type=user['user_type'])
        
        # If Investigator, shows all Completed Orders
        if user['user_type'] == 'investigator':
            orders = defaultdict(int)
            for item in mongo.db.orders.find({'completed':True}):
                #order_id = str(item['_id'])
                #orders.update({
                #        'entree':item['entree'],
                #        'address':item['address'],
                #        'cost':item['cost'],
                #        'restaurant':item['restaurant'],
                #        'completed':item['completed']
                #})
                key = item['entree']
                orders[key] += 1
                
            return render_template('orders.html',orders=orders, user_type=user['user_type'])


        # Everyone else, just shows orders
        orders = {}
        for item in mongo.db.orders.find({'username':session['username']}):
            date_time = item['date'].strftime('%B %d, %Y at %I:%M %p')
            order_id = str(item['_id'])
            orders.update({
                order_id: {
                    'entree':item['entree'],
                    'address':item['address'],
                    'cost':item['cost'],
                    'completed':item['completed'],
                    'date_time':str(date_time)
                }
            })
                #return jsonify(orders)
        return render_template('orders.html',orders=orders)
    else: 
        #TODO Make Prettier, can use flash() and redirect maybe
        return render_template('login_error.html')


@app.route('/purchase/<string:entree>')
def purchase(entree):
    """
    Cart is implemented using Session
    Cart is a list of items picked from menu in session['cart']
    cart = { entree: {'description':'string', 'cost':value, etc.}}
    """
    if session:
        cart = session['cart']
        cart.append(entree)
        session['cart'] = cart
        return redirect('/menu/')
    else:
        cart = []
        cart.append(entree)
        session['cart'] = cart
        return redirect('/menu/')


@app.route('/cart/')
def cart():
    """
    Cart is implemented using Session
    Cart is a list of items picked from menu in session['cart']
    cart = { entree: {'description':'string', 'cost':value, etc.}}
    """
    if session:

        local_cart = session['cart']

        # Turns array into Dict. {item:count}
        temp_cart = Counter(local_cart)
        cart = {}
        total = 0.0

        for entree, count in temp_cart.items():
            for item in mongo.db.menu.find({'entree':entree}):
                total = total + float(item['cost']) * float(count)
                cart.update({
                    item['entree']:{
                        'description': item['description'],
                        'cost': item['cost'], 
                        'image': item['img'],
                        'count': count,
                        'restaurant': item['restaurant']
                        # Need to add zip to cart maybe?
                        #{'zip': item['zip']}
                    }
                })
        
        return render_template('cart.html', cart=cart, total=total)
    else:
        return render_template('login_error.html')

@app.route('/add_item')
def add_item():
    # Add Menu Item (Buddy)
    return render_template('add_item.html')


@app.route('/add_menu_item', methods=['POST'])
def add_menu_item():
    if request.method == 'POST':
        restaurant = mongo.db.users.find_one({'username':session['username']})['restaurant']
        menu = mongo.db.menu
        menu.insert({
            'entree':request.form['entree'],
            'description':request.form['description'],
            'cost':request.form['cost'],
            'img':request.form['image'],
            'restaurant':restaurant
        })
        return redirect(url_for('menu'))


@app.route('/deliver/<string:object_id>')
def deliver(object_id):
    object_id = ObjectId(object_id)
    mongo.db.orders.update({'_id':object_id}, {"$set":{'requested_delivery':True}})

    # Send Message to Patron that Order is requested for Delivery
    order = mongo.db.orders.find_one({'_id':object_id})
    mongo.db.messages.insert({
            'username':order['username'],
            'message':'Your Order has been requested for delivery'
        })

    return redirect('/orders/')


@app.route('/complete_order/<string:object_id>')
def complete_order(object_id):
    object_id = ObjectId(object_id)
    mongo.db.orders.update({'_id':object_id}, {"$set":{'completed':True}})

    # Send Message to Patron that Order has been Delievered
    order = mongo.db.orders.find_one({'_id':object_id})
    mongo.db.messages.insert({
            'username':order['username'],
            'message':'Your order has been Delivered and Completed'
        })
    return redirect('/orders/')


@app.route('/pay/', methods=['POST'])
def pay():
    #output = [request.form['total'], request.form['cart']]
    #return jsonify(output)
    return render_template('pay.html', total=request.form['total'], cart=request.form['cart'])


@app.route('/process', methods=['POST'])
def process():
    # Converts to Dict.
    cart = ast.literal_eval(request.form['cart'])
    name = request.form['name']
    cc_num = request.form['number']
    expiration = request.form['expiry'].split('/')
    cvc = request.form['cvc']

    if name == '' or cc_num == '' or expiration == None or cvc == '': 
        return 'Please enter valid Credit Card Information'
    """
    Cart = {item key:[key:value]}
    """
    orders = mongo.db.orders

    if 'username' in session:
        user = mongo.db.users.find_one({'username': session['username']})
        
        for key, value in cart.items():
            orders.insert({
                'username':session['username'],
                'entree':key,
                'address':user['address'], 
                'cost':value['cost'],
                'count':value['count'],
                'restaurant':value['restaurant'],
                'completed':False,
                'requested_delivery':False,
                'paid':True,
                'date':datetime.now()
            })

        return redirect('/orders/')
    else:
        # Anonymous Customer
        # Need to have user add Address
        for key, value in cart.items():
            orders.insert({
                'username':'anonymous',
                'entree':key,
                'address':'anonymous', 
                'cost':value['cost'],
                'count':value['count'],
                'restaurant':value['restaurant'],
                'completed':False,
                'requested_delivery':False,
                'paid':True,
                'date':datetime.now()
            })
        return redirect('/menu/')

    return 'An Error Has Occured - Pablo'


@app.route('/messages/')
def messages():
    if 'username' in session and \
        session['user_type'] == 'patron':
        user = mongo.db.users.find_one({'username':session['username']})
        messages = {}
        for item in mongo.db.messages.find({'username':user['username']}):
            message_id = str(item['_id'])
            messages.update({
                message_id: {
                    'message':item['message'],
                }
            })
        return render_template('messages.html',messages=messages)
    else:
        # Only Patrons Have messages;To view order updates
        return render_template('login_error.html') 


@app.route('/remove_message/<string:object_id>')
def remove_message(object_id):
    object_id = ObjectId(object_id)
    mongo.db.messages.remove({'_id':object_id})
    return redirect(url_for('messages'))


@app.route('/logout')
def logout():
    if 'user_type' in session:
        # If Chauffeur, Chauffeur if 'off the clock'
        if session['user_type'] == 'chauffeur':
            mongo.db.users.update({'username':session['username']}, {"$set":{'on_clock':False}})
    session.clear()
    return redirect('/')


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


if __name__ == '__main__':
    app.jinja_env.cache = {}
    # SSL Connection
    context = ('server.crt', 'server.key')
    app.run(host='127.0.0.1', port='5000', debug=True, ssl_context='adhoc')
