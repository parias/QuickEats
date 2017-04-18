from flask import Flask, jsonify, render_template, url_for, request, session, redirect, flash
from bson.objectid import ObjectId
from flask_pymongo import PyMongo
from collections import Counter
import bcrypt

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
    #menu = mongo.db.menu.find()
    #return render_template('menu.html', menu=menu)

    menu = {}
    for item in mongo.db.menu.find():
        menu.update({item['entree']:[item['description'],item['cost'], item['img'] ]})
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
                    order_id: [
                        item['entree'],
                        item['address'],
                        item['cost'],
                        item['restaurant'],
                        item['completed']
                    ]})
            return render_template('orders.html',orders=orders, user_type=user['user_type'])

        # If Chauffeur, shows orders than need to be completed
        if user['user_type'] == 'chauffeur':
            orders = {}
            for item in mongo.db.orders.find({'completed':False, 'requested_delivery':True}):
                order_id = str(item['_id'])
                orders.update({
                    order_id: [
                        item['entree'],
                        item['address'],
                        item['cost'],
                        item['restaurant'],
                        item['completed']
                    ]})
            return render_template('orders.html',orders=orders, user_type=user['user_type'])
        
        orders = {}
        for item in mongo.db.orders.find({'username':session['username']}):
            order_id = str(item['_id'])
            orders.update({
                order_id: [
                    item['entree'],
                    item['address'],
                    item['cost'],
                    item['completed']
                    ]})
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
    cart = []
    """
    if session:
        cart = session['cart']
        cart.append(entree)

        session['cart'] = cart
        #return jsonify(session['cart'])
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
    cart = []
    """
    if session:

        local_cart = session['cart']
        temp_cart = Counter(local_cart)
        cart = {}
        total = 0.0
        
        for entree, count in temp_cart.items():
            for item in mongo.db.menu.find({'entree':entree}):
                total = total + float(item['cost']) * float(count)
                cart.update({
                    item['entree']:[
                        item['description'],
                        item['cost'], 
                        item['img'],
                        count
                        ]})

        return render_template('cart.html', cart=cart, total=total)

    else:
        return render_template('login_error.html')

@app.route('/add_item')
def add_item():
    return render_template('add_item.html')

@app.route('/process_item', methods=['POST'])
def process_item():
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
    return redirect('/orders/')

@app.route('/complete_order/<string:object_id>')
def complete_order(object_id):
    object_id = ObjectId(object_id)
    mongo.db.orders.update({'_id':object_id}, {"$set":{'completed':True}})
    return redirect('/orders/')

@app.route('/pay/<float:total>')
def pay(total):
    #return str(total)
    return render_template('pay.html', total=total)

@app.route('/logout')
def logout():

    if 'user_type' in session:
        #return session['user_type']
        if session['user_type'] == 'chauffeur':
            mongo.db.users.update({'username':session['username']}, {"$set":{'on_clock':False}})

    session.clear()
    return redirect('/')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.jinja_env.cache = {}
    app.run(debug=True)
