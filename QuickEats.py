from flask import Flask, jsonify, render_template, url_for, request, session, redirect
from collections import Counter, defaultdict
from datetime import datetime, date, time
from bson.objectid import ObjectId
from flask_pymongo import PyMongo
from OpenSSL import SSL
import operator
import random
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
        return render_template('home_page.html', ads=get_ads(), num_message=num_message(), cart_num=cart_count())
    return render_template('index.html', ads=get_ads(), num_message=num_message(), cart_num=cart_count())


@app.route('/login', methods=['POST'])
def login():
    users = mongo.db.users
    login_user = users.find_one({'username':request.form['username']})

    if login_user:
        if bcrypt.hashpw(request.form['pass'].encode('utf-8'), login_user['password']) == login_user['password']:

            # Adding Request Functionality
            if login_user['verified'] == False:
                return render_template('not_verified.html')

            else:
                session['username'] = request.form['username']
                session['user_type'] = mongo.db.users.find_one({'username':request.form['username']})['user_type']
                user_type = session['user_type']
                if 'cart' not in session:
                    session['cart'] = []
                if user_type == 'chauffeur':
                    mongo.db.users.update({'username':session['username']}, {"$set":{'on_clock':True}})
                return redirect(url_for('home'))
        return render_template('invalid_login.html')

    return render_template('invalid_login.html')


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
                    'zip':request.form['zip'],
                    'state':request.form['state'],
                    'user_type':request.form['user_type'],
                    'verified':True
                    })

            # Removed Captain
            #elif request.form['user_type'] == 'captain':
            #    users.insert({
            #        'username':request.form['username'], 
            #        'password':hashpass, 
            #        'restaurant':request.form['restaurant'],
            #        'user_type':request.form['user_type'],
            #        'on_clock':True,
            #        'verified':False
            #        })
            #    return redirect(url_for('home'))
            
            elif request.form['user_type'] == 'buddy':
                users.insert({
                    'username':request.form['username'], 
                    'password':hashpass, 
                    'restaurant':request.form['restaurant'],
                    'zip':request.form['zip'],
                    'user_type':request.form['user_type'],
                    'on_clock':True,
                    'verified':False
                    })
                return redirect(url_for('home'))
            
            elif request.form['user_type'] == 'chauffeur':
                users.insert({
                    'username':request.form['username'], 
                    'password':hashpass, 
                    'zip':request.form['zip'],
                    'user_type':request.form['user_type'],
                    'on_clock':True,
                    'verified':False
                    })
                return redirect(url_for('home'))
            
            # Removed Nerd Registration
            #elif request.form['user_type'] == 'nerd':
            #    users.insert({
            #        'username':request.form['username'],
            #        'password':hashpass,
            #        'user_type':request.form['user_type'],
            #        'on_clock':True,
            #        'verified':True
            #        })
            #    return redirect(url_for('home'))
            
            elif request.form['user_type'] == 'investigator': 
                users.insert({
                    'username':request.form['username'],
                    'password':hashpass,
                    'user_type':request.form['user_type'],
                    'zip':request.form['zip'],
                    'on_clock':True,
                    'verified':False
                    })
                return redirect(url_for('home'))
            
            else:
                return render_template('registration_error.html')
            
            # Create Session variables when Registering
            session['username'] = request.form['username']
            session['user_type'] = request.form['user_type']
            if 'cart' not in session:
                session['cart'] = []
            return redirect(url_for('home'))

        return 'That username already exists!'

    return render_template('register.html', ads=get_ads(), num_message=num_message(), cart_num=cart_count())


@app.route('/home/')
def home(username=None):
    if 'username' in session:
        return render_template('home_page.html', username=session['username'], ads=get_ads(), num_message=num_message(), cart_num=cart_count())
    else:
        return redirect('/')


@app.route('/menu/')
def menu():
    menu = {}
    if 'username' in session:
        user = mongo.db.users.find_one({'username':session['username']})
        for item in mongo.db.menu.find({'zip':user['zip']}):
            menu.update({
                item['entree']: {
                    'description':item['description'],
                    'cost': item['cost'], 
                    'img': item['img'] 
                }
            })
    else:
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
        return render_template('menu.html', menu=menu, user_type=session['user_type'], ads=get_ads(), num_message=num_message(), cart_num=cart_count())
    else:
        return render_template('menu.html', menu=menu, ads=get_ads(), num_message=num_message(), cart_num=cart_count())


@app.route('/orders/')
def orders():
    ads = 'hello ads world'
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
                        'username':item['username'],
                        'address':item['address'],
                        'cost':item['cost'],
                        'restaurant':item['restaurant'],
                        'requested_delivery':item['requested_delivery'],
                        'completed':item['completed'],
                        'count':item['count']
                    }
                })
                
            return render_template('orders.html', orders=orders, user_type=user['user_type'], ads=get_ads(), num_message=num_message(), cart_num=cart_count())

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
                        'completed':item['completed'],
                        'count':item['count'],
                        'username':item['username']
                    }
                })
                    
            #return jsonify(orders)
            return render_template('orders.html', orders=orders, user_type=user['user_type'], ads=get_ads(), num_message=num_message(), cart_num=cart_count())
        
        # If Investigator, shows all Completed Orders
        if user['user_type'] == 'investigator':
            orders = []
            ads = {}
            
            # Adds adds all orders to list, then converts to dict with counting
            # ex: {'waffles':4, 'Cake':2, ...}
            for item in mongo.db.orders.find({'completed':True}):
                orders.append(item['entree'])
            orders = Counter(orders)
            
            # Creates Dict with Menu Item ID, entree name, and number of times ordered
            for entree in orders:
                menu_item = mongo.db.menu.find_one({'entree':entree})
                menu_id = str(menu_item['_id'])
                ads.update({
                    menu_id: {
                        'entree':entree,
                        'num_orders': orders[entree]
                    }
                })
                
            return render_template('orders.html', orders=ads, user_type=user['user_type'], ads=get_ads(), num_message=num_message(), cart_num=cart_count())


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
                    'date_time':str(date_time),
                    'count':item['count']
                }
            })
        return render_template('orders.html', orders=orders, ads=get_ads(), num_message=num_message(), cart_num=cart_count())
    else: 
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


@app.route('/ad_click/<string:entree>')
def ad_click(entree):
    """
    Cart is implemented using Session
    Cart is a list of items picked from menu in session['cart']
    cart = { entree: {'description':'string', 'cost':value, etc.}}
    """
    if session:
        cart = session['cart']
        cart.append(entree)
        session['cart'] = cart
    else:
        cart = []
        cart.append(entree)
        session['cart'] = cart
    return redirect(url_for('cart'))


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
        
        return render_template('cart.html', cart=cart, total=total, ads=get_ads(), num_message=num_message(), cart_num=cart_count())
    else:
        return render_template('login_error.html')

@app.route('/add_item')
def add_item():
    # Add Menu Item (Buddy)
    return render_template('add_item.html', ads=get_ads(), num_message=num_message(), cart_num=cart_count())


@app.route('/add_menu_item', methods=['POST'])
def add_menu_item():
    if request.method == 'POST':
        user = mongo.db.users.find_one({'username':session['username']})
        restaurant = user['restaurant']
        zip_code = user['zip']
        user = mongo.db.users.find_one({})
        menu = mongo.db.menu
        menu.insert({
            'entree':request.form['entree'],
            'description':request.form['description'],
            'cost':request.form['cost'],
            'img':request.form['image'],
            'restaurant':restaurant,
            'zip':zip_code
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
            'message':'Your Order has been requested for delivery',
            'time': datetime.now()
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
            'message':'Your order has been Delivered and Completed',
            'time':datetime.now()
        })
    return redirect('/orders/')


@app.route('/pay/', methods=['POST'])
def pay():
    if 'username' not in session:
        return render_template('login_error.html')
    else:
        return render_template('pay.html', total=request.form['total'], cart=request.form['cart'], ads=get_ads(), num_message=num_message(), cart_num=cart_count())


@app.route('/process', methods=['POST'])
def process():
        # Converts to Dict.
    cart = ast.literal_eval(request.form['cart'])
    name = request.form['name']
    cc_num = request.form['number']
    expiration = request.form['expiry'].split('/')
    cvc = request.form['cvc']

    if int(expiration[0]) < 1 or int(expiration[0]) > 12:
        return render_template('credit_error.html')
    if int(expiration[1]) < 2017 or int(expiration[1]) > 2025:
        return render_template('credit_error.html')

    if name == '' or cc_num == '' or len(expiration) != 2 or expiration[1] == '' or cvc == '': 
        return render_template('credit_error.html')
    """
    Cart = {item key:[key:value]}
    """
    orders = mongo.db.orders

    if 'username' in session:
        if session['user_type'] == 'patron':
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
            session['cart'] = []
            return redirect('/orders/')
        else:
            return render_template('address_error.html')
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
        session['cart'] = []
        return redirect('/menu/')

    return render_template('credit_error.html')


@app.route('/messages/')
def messages():
    if 'username' in session and \
        session['user_type'] == 'patron':
        user = mongo.db.users.find_one({'username':session['username']})
        messages = {}
        for item in mongo.db.messages.find({'username':user['username']}):
            message_id = str(item['_id'])
            date_time = item['time'].strftime('%B %d, %Y at %I:%M %p')
            messages.update({
                message_id: {
                    'message':item['message'],
                    'date_time': date_time
                }
            })
        return render_template('messages.html',messages=messages, user_type=session['user_type'], ads=get_ads(), num_message=num_message(), cart_num=cart_count())
    elif 'username' in session and \
            session['user_type'] == 'nerd':
        messages = {}
        for item in mongo.db.users.find({'verified':False}):
            message_id = str(item['_id'])
            messages.update({
                message_id:{
                    'message':item['username'] + ' requested for employee elevation'
                }
            })
        return render_template('messages.html', messages=messages, user_type=session['user_type'], ads=get_ads(), num_message=num_message(), cart_num=cart_count())
    else:
        # Only Patrons and Nerds Have messages;To view order updates
        return render_template('user_error.html') 


@app.route('/remove_message/<string:object_id>')
def remove_message(object_id):
    object_id = ObjectId(object_id)
    mongo.db.messages.remove({'_id':object_id})
    return redirect(url_for('messages'))


@app.route('/create_ad/<string:object_id>')
def create_ad(object_id):
    object_id = ObjectId(object_id)
    menu_item = mongo.db.menu.find_one({'_id':object_id})

    # Unique ads
    mongo.db.ads.update(
            {'item_name':menu_item['entree']},
            {"$set": {'message':'Order Now!', 'img':menu_item['img'], 'menu_item':object_id}},
            upsert=True
    )
    return redirect(url_for('orders'))


@app.route('/elevate/<string:object_id>')
def elevate(object_id):
    if session['user_type'] == 'nerd':
        object_id = ObjectId(object_id)
        mongo.db.users.update({'_id':object_id}, {"$set":{'verified':True}})
        return redirect(url_for('messages'))
    else:
        return render_template('user_error.html')


@app.route('/reject/<string:object_id>')
def reject(object_id):
    if session['user_type'] == 'nerd':
        object_id = ObjectId(object_id)
        mongo.db.users.remove({'_id':object_id})
        return redirect(url_for('messages'))
    else:
        return render_template('user_error.html')


@app.route('/logout')
def logout():
    if 'user_type' in session:
        # If Chauffeur, Chauffeur if 'off the clock'
        if session['user_type'] == 'chauffeur':
            mongo.db.users.update({'username':session['username']}, {"$set":{'on_clock':False}})
    session.clear()
    return redirect('/')


@app.route('/clear_cart')
def clear_cart():
    session['cart'] = []
    return redirect(url_for('cart'))


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


def get_ads():
    # What do you think this does?
    all_ads = {}
    for item in mongo.db.ads.find({}):
        all_ads.update({
            item['item_name']: {
                'image':item['img'],
                'menu_item_id':str(item['menu_item']),
                'message':item['message']
            }
        })

    foods = []
    for item in mongo.db.ads.find({}):
        foods.append(item['item_name'])
        
    ads = []
    for i in range(4):
        num_ads = len(all_ads) - 1
        entree = foods[random.randint(0,num_ads)]
        ads.append({ entree:all_ads[entree] })

    return ads


def num_message():
    count = 0
    if 'username' in session:
        if session['user_type'] == 'nerd':
            for item in mongo.db.users.find({'verified':False}):
                count += 1
        if session['user_type'] == 'patron':
            for item in mongo.db.messages.find({'username':session['username']}):
                count += 1
    return count


def cart_count():
    count = 0
    if 'cart' in session:
        for item in session['cart']:
            count+=1
    return count


@app.route('/home_page')
def home_page():
    return render_template('home_page.html', ads=get_ads(), num_message=num_message(), cart_num=cart_count())


if __name__ == '__main__':
    app.jinja_env.cache = {}
    context = ('server.crt', 'server.key')
    #app.run(host='127.0.0.1',debug=True)
    app.run(host='0.0.0.0',debug=True, ssl_context=context)
    #app.run(host='127.0.0.1', debug=True, ssl_context=context, threaded=True)
