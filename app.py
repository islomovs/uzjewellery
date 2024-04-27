from flask import Flask, flash, redirect, render_template, request, url_for
from markupsafe import Markup
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_admin.form.upload import ImageUploadField
from flask_migrate import Migrate
import os
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from PIL import Image
from werkzeug.security import generate_password_hash, check_password_hash



app = Flask(__name__, static_folder='static', template_folder='./templates')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cards.db'
app.config['SECRET_KEY'] = 'your_persistent_secret_key'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static/images/uploads/')
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        access = current_user.is_authenticated
        print(f"Access to admin: {access}")  # Debugging output
        return access

    def inaccessible_callback(self, name, **kwargs):
        print("Redirecting to login page")  # Debugging output
        return redirect(url_for('login', next=request.url))

@app.route('/create_user')
def create_user():
    user = User(username='admin')
    user.set_password('uzJewell654123')
    db.session.add(user)
    db.session.commit()
    return 'User created successfully!'

@app.route('/show_users')
def show_users():
    users = User.query.all()
    return ', '.join([u.username for u in users])


@app.route('/test_login')
def test_login():
    if current_user.is_authenticated:
        return f"Logged in as {current_user.username}"
    else:
        return "Not logged in"


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next') or url_for('admin.index')
            print(f"Redirecting to {next_page}")  # Debugging output
            return redirect(next_page)
        else:
            flash('Invalid username or password')
    return render_template('login.html')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


class Card(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.String(10))
    
    # English fields
    title_en = db.Column(db.String(100))
    description_en = db.Column(db.String(500))
    
    # Russian fields
    title_ru = db.Column(db.String(100))
    description_ru = db.Column(db.String(500))
    
    # Uzbek fields
    title_uz = db.Column(db.String(100))
    description_uz = db.Column(db.String(500))
    
    image_filename = db.Column(db.String(255))  # This will store the filename of the image

    def __repr__(self):
        return f"Card('{self.title_en}', '{self.id}')"

class CardAdmin(ModelView):
    form_extra_fields = {
        'image_filename': ImageUploadField('Image',
                                           base_path=app.config['UPLOAD_FOLDER'],
                                           url_relative_path='uploads/',
                                           allowed_extensions=['jpg', 'png', 'gif'])
    }

    def _list_thumbnail(view, context, model, name):
        if not getattr(model, 'image_filename', None):
            return ''
        return Markup(f'<img src="{url_for("static", filename="images/uploads/" + model.image_filename)}" style="height:50px;">')

    column_formatters = {
        'image_filename': _list_thumbnail
    }

    def on_model_delete(self, model):
        """Handle image file deletion when the corresponding database record is deleted."""
        if model.image_filename:
            try:
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], model.image_filename))
                print(f"Deleted image {model.image_filename}")
            except OSError as e:
                print(f"Error deleting image {model.image_filename}: {e}")

admin = Admin(app, index_view=MyAdminIndexView(), template_mode='bootstrap3')
admin.add_view(CardAdmin(Card, db.session))



@app.route('/')
def index():
    return render_template('./en/index.html')

@app.route('/en')
def en():
    return render_template('./en/index.html')


@app.route('/en/about')
def about():
    paragraph1 = "On May 24-26, 2024, in the ancient city of Samarkand, Uzbekistan, the II International Exhibition-Trade of modern equipment, technologies, and jewellery of the jewellery industry, 'UZBEK JEWELLERYFAIR-2024,' will be held. As a result of the reforms implemented in the development of the jewelry industry in recent years,a number of positive results have been achieved in the sector. Particularly, in2023, the volume of jewelry production reached 6 450.0 kg, worth 2 050.0billion sums. Currently, the processing capacity of enterprises for precious metals has reached 18 tons, which has increased by 1.2 times compared to 2022."
    paragraph2 = "The exhibition-trade held in Tashkent in May 2023 was recognized by participants and more than 3,000 visitors. Notably, over 50domestic and foreign enterprises signed cooperation agreements worth $100million and made additional sales. Foreign entrepreneurs were allowed to import their exhibits based on favorable customs conditions."
    paragraph3 = "Nearly 90 million people live in the region, and Uzbekistan is taking determined steps to become the jewellery industry hub of Central Asia. Presently, Uzbekistan ranks among the top 10 gold mining countries. The country's legislative parameters also offer favorable conditions for representatives of the jewellery industry; for example, there is an opportunity to purchase precious metals through direct contracts and stock exchanges. Overall, the country is emerging as the center of the new jewellery industry in the civilized world. Furthermore, in May 2024, Samarkand will host the international jewelry trade exhibition \"UZBEK JEWELLERY FAIR-2024\" for representatives of the world jewelry industry. The ancient garden of the east – this is what ancientand modern authors called Samarkand. This city is an amazing land that attracts the attention of people from all over the world with its unique history and wealth of spiritual heritage."
    return render_template('./en/about.html', paragraph1=paragraph1, paragraph2=paragraph2, paragraph3=paragraph3)

@app.route('/en/catalog')
def catalog():
    cards = Card.query.order_by(Card.year.desc()).all()
    cards_by_year = {}
    for card in cards:
        if card.year not in cards_by_year:
            cards_by_year[card.year] = []
        cards_by_year[card.year].append({
            'id': card.id,
            'title': card.title_en,
            'description': card.description_en,
            'image_filename': card.image_filename
        })

    return render_template('./en/catalog.html', cards_by_year=cards_by_year)

@app.route('/en/catalog/company-<int:card_id>')
def company_detail(card_id):
    card = Card.query.get_or_404(card_id)
    details = {
        'title': card.title_en,
        'description': card.description_en,
        'image_filename': card.image_filename
    }
    return render_template('./en/company.html', card=details)

@app.route('/ru')
def ru():
    return render_template('./ru/index.html')


@app.route('/ru/about')
def ru_about():
    paragraph1 = "24-26 мая 2024 года в древнем городе Узбекистана Самарканде пройдет II международная выставка-ярмарка современного оборудования, технологий и ювелирных изделий ювелирной отрасли «UZBEK JEWELLERY FAIR-2024»."
    paragraph2 = "Выставка-ярмарка, состоявшаяся в Ташкенте, в мае 2023 года, получила признание участников и более 3000 посетителей. В частности, более 50 отечественных и зарубежных предприятий подписали соглашения о сотрудничестве и в рамках выставки реализовали ювелирных изделий на сумму превышающую 100 млн. долл. Зарубежным участникам было разрешено ввозить ювелирные и другие изделия  из драгоценных металлов и драгоценных камней на льготных таможенных условиях."
    paragraph3 = "В центрально азиатском регионе проживает более 90 миллионов человек. Республика Узбекистан предпринимает большие шаги, чтобы стать центром ювелирной промышленности Центральной Азии. На сегодняшний день Узбекистан входит в ТОП-10 золотодобывающих стран. Законодательством страны предусмотрены выгодные предложения для представителей бизнеса ювелирной отрасли, например, у производителей есть возможность приобретения драгоценных металлов по прямым договорам и(или) через биржевые торги. Импорт и реализация драгоценных камней полностью освобождены от НДС.  Уже сегодня можно сказать, что страна становится новым центром мировой ювелирной индустрии."
    return render_template('./ru/about.html', paragraph1=paragraph1, paragraph2=paragraph2, paragraph3=paragraph3)

@app.route('/ru/catalog')
def ru_catalog():
    cards = Card.query.order_by(Card.year.desc()).all()
    cards_by_year = {}
    for card in cards:
        if card.year not in cards_by_year:
            cards_by_year[card.year] = []
        cards_by_year[card.year].append({
            'id': card.id,
            'title': card.title_ru,
            'description': card.description_ru,
            'image_filename': card.image_filename
        })

    return render_template('./ru/catalog.html', cards_by_year=cards_by_year)

@app.route('/ru/catalog/company-<int:card_id>')
def ru_company_detail(card_id):
    card = Card.query.get_or_404(card_id)
    details = {
        'title': card.title_ru,
        'description': card.description_ru,
        'image_filename': card.image_filename
    }
    return render_template('./ru/company.html', card=details)

@app.route('/uz')
def uz():
    return render_template('./uz/index.html')


@app.route('/uz/about')
def uz_about():
    paragraph1 = "2024-yilning 24-26-may kunlari, O‘zbekistonning qadimiy Samarqand shahrida zargarlik sanoatining zamonaviy uskuna, texnologiyalari va zargarlik buyumlari \"UZBEK JEWELLERY FAIR-2024\" II xalqaro ko‘rgazma-savdosi bo‘lib o‘tadi."
    paragraph2 = "2023-yil may oyida Toshkent shahrida o‘tkazilgan ko‘rgazma-savdosi - ishtirokchilar va 3000 dan ortiq tashrif buyuruvchilarining e’tirofiga sazovor bo‘lgandi. Xususan, mazkur ko‘rgazma-savdosida 50 dan ortiq mahalliy va xorijiy korxonalar 100 mln. dollarga yaqin hamkorlik shartnomalarini imzolashgan va sotuv amalga oshirishgan. Xorijiy tadbirkorlarning qulay bojxona shartlari asosida o‘z mahsulotlarini olib kirishlariga ruxsat berildi."
    paragraph3 = "Mintaqada 90 milliondan ortiq aholi istiqomat qiladi. O‘zbekiston esa Markaziy Osiyoning zargarlik sanoati xabi bo‘lish uchun yirik qadamlar tashlamoqda.  Bugungi kunda O‘zbekiston oltin qazib oluvchi TOP-10 mamlakatlardan biri hisoblanadi. Mamlakat qonunchilik parametrlari ham zargarlik sanoati biznesi vakillari uchun qulay takliflarga ega, masalan: qimmatbaho metallarni to‘g‘ridan-to‘g‘ri shartnomalar va birja savdolari orqali xarid qilish imkoniyati mavjud. Zargarlik sanoati tarmog‘i va qimmatbaho toshlar importi mamlakatda butunlay QQS ozod etilgan. Bir so‘z bilan aytganda mamlakat - sivilizatsion dunyoning yangi zargarlik sanoati markaziga aylanib bormoqda."
    return render_template('./uz/about.html', paragraph1=paragraph1, paragraph2=paragraph2, paragraph3=paragraph3)

@app.route('/uz/catalog')
def uz_catalog():
    cards = Card.query.order_by(Card.year.desc()).all()
    cards_by_year = {}
    for card in cards:
        if card.year not in cards_by_year:
            cards_by_year[card.year] = []
        cards_by_year[card.year].append({
            'id': card.id,
            'title': card.title_uz,
            'description': card.description_uz,
            'image_filename': card.image_filename
        })

    return render_template('./uz/catalog.html', cards_by_year=cards_by_year)

@app.route('/uz/catalog/company-<int:card_id>')
def uz_company_detail(card_id):
    card = Card.query.get_or_404(card_id)
    details = {
        'title': card.title_uz,
        'description': card.description_uz,
        'image_filename': card.image_filename
    }
    return render_template('./uz/company.html', card=details)


@app.cli.command("init-db")
def init_db_command():
    """Clear the existing data and create new tables."""
    db.drop_all()
    db.create_all()
    print("Initialized the database.")

migrate = Migrate(app, db)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)