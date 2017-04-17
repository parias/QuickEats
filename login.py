from flask import Flask, jsonify, render_template, url_for, request, session, redirect, flash
from collections import Counter
from flask_pymongo import PyMongo
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
    login_user = users.find_one({'name':request.form['username']})
    
    if login_user:
        if bcrypt.hashpw(request.form['pass'].encode('utf-8'), login_user['password']) == login_user['password']:
            session['username'] = request.form['username']
            session["cart"] = []
            return redirect(url_for('home'))
        return 'Invalid username/password combination'

    return 'Invalid username/password combination'

@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        users = mongo.db.users
        existing_user = users.find_one({'name':request.form['username']})

        if existing_user is None:
            hashpass = bcrypt.hashpw(request.form['pass'].encode('utf-8'), bcrypt.gensalt())
            users.insert({
                'username':request.form['username'], 
                'password':hashpass, 
                'address':request.form['address'], 
                'city':request.form['city'], 
                'state':request.form['state']
            })
            session['username'] = request.form['username']
            return redirect(url_for('home'))

        return 'That username already exists!'

    return render_template('register.html')

@app.route('/home/')
def home(username=None):
    if session:
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
    return render_template('menu.html',menu=menu)

@app.route('/orders/')
def orders():
    # current_user = session['username']
    if session:
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
    cart = session['cart']
    cart.append(entree)

    session['cart'] = cart
    #return jsonify(session['cart'])
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

        for entree, count in temp_cart.items():
            for item in mongo.db.menu.find({'entree':entree}):
                cart.update({
                    item['entree']:[
                        item['description'],
                        item['cost'], 
                        item['img'],
                        count
                    ]})
        
        #return jsonify(cart)
        return render_template('cart.html', cart=cart)

    else:
        return render_template('login_error.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.jinja_env.cache = {}
    app.run(debug=True)



