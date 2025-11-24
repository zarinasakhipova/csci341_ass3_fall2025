
from flask import Flask, render_template, request, redirect, url_for, flash
from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, String, Float, Date, Text, Boolean, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
import os
import logging

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql+psycopg2://postgres:2004@localhost:5432/caregivers_platform')
logger.info(f"Connecting to database: {DATABASE_URL.replace(DATABASE_URL.split('@')[0], '***:***')}")

try:
    engine = create_engine(DATABASE_URL, echo=True)
    Session = sessionmaker(bind=engine)

    # Создание таблиц если они не существуют
    with engine.connect() as conn:
        # Тест подключения
        conn.execute(text("SELECT 1"))

        # Создание таблиц
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS "USER" (
                user_id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                given_name VARCHAR(100) NOT NULL,
                surname VARCHAR(100) NOT NULL,
                city VARCHAR(100),
                phone_number VARCHAR(20),
                profile_description TEXT,
                password VARCHAR(255) NOT NULL
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS CAREGIVER (
                caregiver_user_id INTEGER PRIMARY KEY REFERENCES "USER"(user_id),
                photo VARCHAR(500),
                gender VARCHAR(10),
                caregiving_type VARCHAR(50),
                hourly_rate DECIMAL(10,2)
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS MEMBER (
                member_user_id INTEGER PRIMARY KEY REFERENCES "USER"(user_id),
                house_rules TEXT,
                dependent_description TEXT
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ADDRESS (
                member_user_id INTEGER REFERENCES MEMBER(member_user_id),
                house_number VARCHAR(20),
                street VARCHAR(200),
                town VARCHAR(100),
                PRIMARY KEY (member_user_id)
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS JOB (
                job_id SERIAL PRIMARY KEY,
                member_user_id INTEGER REFERENCES MEMBER(member_user_id),
                required_caregiving_type VARCHAR(50),
                other_requirements TEXT,
                date_posted DATE
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS JOB_APPLICATION (
                caregiver_user_id INTEGER REFERENCES CAREGIVER(caregiver_user_id),
                job_id INTEGER REFERENCES JOB(job_id),
                date_applied DATE,
                PRIMARY KEY (caregiver_user_id, job_id)
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS APPOINTMENT (
                appointment_id SERIAL PRIMARY KEY,
                caregiver_user_id INTEGER REFERENCES CAREGIVER(caregiver_user_id),
                member_user_id INTEGER REFERENCES MEMBER(member_user_id),
                appointment_date DATE,
                appointment_time TIME,
                work_hours INTEGER NOT NULL,
                status VARCHAR(20) DEFAULT 'pending'
            )
        """))

        conn.commit()

    logger.info("Database connection successful and tables created!")

except Exception as e:
    logger.error(f"Database setup failed: {e}")
    raise

# Table configurations
TABLE_CONFIGS = {
    'users': {
        'table': '"USER"',
        'id_field': 'user_id',
        'list_query': 'SELECT * FROM "USER" ORDER BY user_id',
        'columns': [
            {'key': 'user_id', 'label': 'ID', 'type': 'text'},
            {'key': 'email', 'label': 'Email', 'type': 'text'},
            {'key': 'given_name', 'label': 'Given Name', 'type': 'text'},
            {'key': 'surname', 'label': 'Surname', 'type': 'text'},
            {'key': 'city', 'label': 'City', 'type': 'text'},
            {'key': 'phone_number', 'label': 'Phone', 'type': 'text'}
        ],
        'create_fields': [
            {'name': 'email', 'label': 'Email', 'type': 'email', 'required': True},
            {'name': 'given_name', 'label': 'Given Name', 'type': 'text', 'required': True},
            {'name': 'surname', 'label': 'Surname', 'type': 'text', 'required': True},
            {'name': 'city', 'label': 'City', 'type': 'text', 'required': False},
            {'name': 'phone_number', 'label': 'Phone Number', 'type': 'text', 'required': False},
            {'name': 'profile_description', 'label': 'Profile Description', 'type': 'textarea', 'required': False},
            {'name': 'password', 'label': 'Password', 'type': 'password', 'required': True}
        ],
        'insert_fields': ['email', 'given_name', 'surname', 'city', 'phone_number', 'profile_description', 'password'],
        'update_fields': ['email', 'given_name', 'surname', 'city', 'phone_number', 'profile_description', 'password']
    },
    'caregivers': {
        'table': 'CAREGIVER',
        'id_field': 'caregiver_user_id',
        'list_query': '''SELECT c.*, u.given_name, u.surname, u.email
                        FROM CAREGIVER c JOIN "USER" u ON c.caregiver_user_id = u.user_id
                        ORDER BY c.caregiver_user_id''',
        'columns': [
            {'key': 'caregiver_user_id', 'label': 'User ID', 'type': 'text'},
            {'key': 'given_name', 'label': 'Name', 'type': 'text'},
            {'key': 'email', 'label': 'Email', 'type': 'text'},
            {'key': 'gender', 'label': 'Gender', 'type': 'text'},
            {'key': 'caregiving_type', 'label': 'Type', 'type': 'text'},
            {'key': 'hourly_rate', 'label': 'Hourly Rate', 'type': 'money'}
        ],
        'create_fields': [
            {'name': 'caregiver_user_id', 'label': 'User ID', 'type': 'select', 'required': True, 'options_query': 'SELECT user_id, given_name, surname FROM "USER" ORDER BY user_id'},
            {'name': 'photo', 'label': 'Photo URL', 'type': 'text', 'required': False},
            {'name': 'gender', 'label': 'Gender', 'type': 'select', 'required': False, 'options': [{'value': 'Male', 'label': 'Male'}, {'value': 'Female', 'label': 'Female'}]},
            {'name': 'caregiving_type', 'label': 'Caregiving Type', 'type': 'select', 'required': False, 'options': [{'value': 'babysitter', 'label': 'Babysitter'}, {'value': 'elderly care', 'label': 'Elderly Care'}, {'value': 'playmate', 'label': 'Playmate'}]},
            {'name': 'hourly_rate', 'label': 'Hourly Rate', 'type': 'number', 'required': True, 'step': '0.01'}
        ],
        'insert_fields': ['caregiver_user_id', 'photo', 'gender', 'caregiving_type', 'hourly_rate'],
        'update_fields': ['photo', 'gender', 'caregiving_type', 'hourly_rate']
    },
    'members': {
        'table': 'MEMBER',
        'id_field': 'member_user_id',
        'list_query': '''SELECT m.*, u.given_name, u.surname, u.email
                        FROM MEMBER m JOIN "USER" u ON m.member_user_id = u.user_id
                        ORDER BY m.member_user_id''',
        'columns': [
            {'key': 'member_user_id', 'label': 'User ID', 'type': 'text'},
            {'key': 'given_name', 'label': 'Name', 'type': 'text'},
            {'key': 'email', 'label': 'Email', 'type': 'text'},
            {'key': 'house_rules', 'label': 'House Rules', 'type': 'text_long'},
            {'key': 'dependent_description', 'label': 'Dependent Description', 'type': 'text_long'}
        ],
        'create_fields': [
            {'name': 'member_user_id', 'label': 'User ID', 'type': 'select', 'required': True, 'options_query': 'SELECT user_id, given_name, surname FROM "USER" ORDER BY user_id'},
            {'name': 'house_rules', 'label': 'House Rules', 'type': 'textarea', 'required': False},
            {'name': 'dependent_description', 'label': 'Dependent Description', 'type': 'textarea', 'required': False}
        ],
        'insert_fields': ['member_user_id', 'house_rules', 'dependent_description'],
        'update_fields': ['house_rules', 'dependent_description']
    },
    'addresses': {
        'table': 'ADDRESS',
        'id_field': 'member_user_id',
        'list_query': '''SELECT a.*, u.given_name, u.surname
                        FROM ADDRESS a JOIN MEMBER m ON a.member_user_id = m.member_user_id
                        JOIN "USER" u ON m.member_user_id = u.user_id
                        ORDER BY a.member_user_id''',
        'columns': [
            {'key': 'member_user_id', 'label': 'Member ID', 'type': 'text'},
            {'key': 'given_name', 'label': 'Member Name', 'type': 'text'},
            {'key': 'house_number', 'label': 'House Number', 'type': 'text'},
            {'key': 'street', 'label': 'Street', 'type': 'text'},
            {'key': 'town', 'label': 'Town', 'type': 'text'}
        ],
        'create_fields': [
            {'name': 'member_user_id', 'label': 'Member ID', 'type': 'select', 'required': True, 'options_query': 'SELECT member_user_id FROM MEMBER ORDER BY member_user_id'},
            {'name': 'house_number', 'label': 'House Number', 'type': 'text', 'required': False},
            {'name': 'street', 'label': 'Street', 'type': 'text', 'required': False},
            {'name': 'town', 'label': 'Town', 'type': 'text', 'required': False}
        ],
        'insert_fields': ['member_user_id', 'house_number', 'street', 'town'],
        'update_fields': ['house_number', 'street', 'town']
    },
    'jobs': {
        'table': 'JOB',
        'id_field': 'job_id',
        'list_query': '''SELECT j.*, u.given_name, u.surname
                        FROM JOB j JOIN MEMBER m ON j.member_user_id = m.member_user_id
                        JOIN "USER" u ON m.member_user_id = u.user_id
                        ORDER BY j.job_id''',
        'columns': [
            {'key': 'job_id', 'label': 'Job ID', 'type': 'text'},
            {'key': 'given_name', 'label': 'Member', 'type': 'text'},
            {'key': 'required_caregiving_type', 'label': 'Type', 'type': 'text'},
            {'key': 'other_requirements', 'label': 'Requirements', 'type': 'text_long'},
            {'key': 'date_posted', 'label': 'Date Posted', 'type': 'text'}
        ],
        'create_fields': [
            {'name': 'member_user_id', 'label': 'Member ID', 'type': 'select', 'required': True, 'options_query': 'SELECT member_user_id FROM MEMBER ORDER BY member_user_id'},
            {'name': 'required_caregiving_type', 'label': 'Required Caregiving Type', 'type': 'select', 'required': False, 'options': [{'value': 'babysitter', 'label': 'Babysitter'}, {'value': 'elderly care', 'label': 'Elderly Care'}, {'value': 'playmate', 'label': 'Playmate'}]},
            {'name': 'other_requirements', 'label': 'Other Requirements', 'type': 'textarea', 'required': False},
            {'name': 'date_posted', 'label': 'Date Posted', 'type': 'date', 'required': False}
        ],
        'insert_fields': ['member_user_id', 'required_caregiving_type', 'other_requirements', 'date_posted'],
        'update_fields': ['required_caregiving_type', 'other_requirements', 'date_posted']
    },
    'job_applications': {
        'table': 'JOB_APPLICATION',
        'id_field': None,
        'list_query': '''SELECT ja.*, u1.given_name AS caregiver_name, u1.surname AS caregiver_surname,
                        u2.given_name AS member_name, u2.surname AS member_surname
                        FROM JOB_APPLICATION ja
                        JOIN CAREGIVER c ON ja.caregiver_user_id = c.caregiver_user_id
                        JOIN "USER" u1 ON c.caregiver_user_id = u1.user_id
                        JOIN JOB j ON ja.job_id = j.job_id
                        JOIN MEMBER m ON j.member_user_id = m.member_user_id
                        JOIN "USER" u2 ON m.member_user_id = u2.user_id
                        ORDER BY ja.job_id, ja.caregiver_user_id''',
        'columns': [
            {'key': 'job_id', 'label': 'Job ID', 'type': 'text'},
            {'key': 'caregiver_name', 'label': 'Caregiver', 'type': 'text'},
            {'key': 'member_name', 'label': 'Member', 'type': 'text'},
            {'key': 'date_applied', 'label': 'Date Applied', 'type': 'text'}
        ],
        'create_fields': [
            {'name': 'caregiver_user_id', 'label': 'Caregiver User ID', 'type': 'select', 'required': True, 'options_query': 'SELECT caregiver_user_id FROM CAREGIVER ORDER BY caregiver_user_id'},
            {'name': 'job_id', 'label': 'Job ID', 'type': 'select', 'required': True, 'options_query': 'SELECT job_id FROM JOB ORDER BY job_id'},
            {'name': 'date_applied', 'label': 'Date Applied', 'type': 'date', 'required': False}
        ],
        'insert_fields': ['caregiver_user_id', 'job_id', 'date_applied'],
        'update_fields': []
    },
    'appointments': {
        'table': 'APPOINTMENT',
        'id_field': 'appointment_id',
        'list_query': '''SELECT a.*, u1.given_name AS caregiver_name, u1.surname AS caregiver_surname,
                        u2.given_name AS member_name, u2.surname AS member_surname
                        FROM APPOINTMENT a
                        JOIN CAREGIVER c ON a.caregiver_user_id = c.caregiver_user_id
                        JOIN "USER" u1 ON c.caregiver_user_id = u1.user_id
                        JOIN MEMBER m ON a.member_user_id = m.member_user_id
                        JOIN "USER" u2 ON m.member_user_id = u2.user_id
                        ORDER BY a.appointment_id''',
        'columns': [
            {'key': 'appointment_id', 'label': 'ID', 'type': 'text'},
            {'key': 'caregiver_name', 'label': 'Caregiver', 'type': 'text'},
            {'key': 'member_name', 'label': 'Member', 'type': 'text'},
            {'key': 'appointment_date', 'label': 'Date', 'type': 'text'},
            {'key': 'appointment_time', 'label': 'Time', 'type': 'text'},
            {'key': 'work_hours', 'label': 'Hours', 'type': 'text'},
            {'key': 'status', 'label': 'Status', 'type': 'text'}
        ],
        'create_fields': [
            {'name': 'caregiver_user_id', 'label': 'Caregiver User ID', 'type': 'select', 'required': True, 'options_query': 'SELECT caregiver_user_id FROM CAREGIVER ORDER BY caregiver_user_id'},
            {'name': 'member_user_id', 'label': 'Member User ID', 'type': 'select', 'required': True, 'options_query': 'SELECT member_user_id FROM MEMBER ORDER BY member_user_id'},
            {'name': 'appointment_date', 'label': 'Appointment Date', 'type': 'date', 'required': False},
            {'name': 'appointment_time', 'label': 'Appointment Time', 'type': 'time', 'required': False},
            {'name': 'work_hours', 'label': 'Work Hours', 'type': 'number', 'required': True},
            {'name': 'status', 'label': 'Status', 'type': 'select', 'required': False, 'options': [{'value': 'pending', 'label': 'Pending'}, {'value': 'accepted', 'label': 'Accepted'}, {'value': 'declined', 'label': 'Declined'}]}
        ],
        'insert_fields': ['caregiver_user_id', 'member_user_id', 'appointment_date', 'appointment_time', 'work_hours', 'status'],
        'update_fields': ['appointment_date', 'appointment_time', 'work_hours', 'status']
    }
}

def get_options_from_query(query):
    session = Session()
    try:
        result = session.execute(text(query))
        options = []
        for row in result:
            row_dict = dict(row._mapping)
            if 'user_id' in row_dict:
                label = f"{row_dict['user_id']} - {row_dict.get('given_name', '')} {row_dict.get('surname', '')}"
                value = row_dict['user_id']
            elif 'member_user_id' in row_dict:
                label = str(row_dict['member_user_id'])
                value = row_dict['member_user_id']
            elif 'caregiver_user_id' in row_dict:
                label = str(row_dict['caregiver_user_id'])
                value = row_dict['caregiver_user_id']
            elif 'job_id' in row_dict:
                label = str(row_dict['job_id'])
                value = row_dict['job_id']
            else:
                label = str(list(row_dict.values())[0])
                value = list(row_dict.values())[0]
            options.append({'value': value, 'label': label})
        return options
    finally:
        session.close()

@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        return "Internal Server Error", 500

@app.route('/db-test')
def db_test():
    """Тест подключения к базе данных"""
    try:
        session = Session()
        result = session.execute(text("SELECT 1 as test"))
        row = result.fetchone()
        session.close()

        db_info = {
            'status': 'Connected',
            'test_result': row[0],
            'database_url': DATABASE_URL.replace(DATABASE_URL.split('@')[0] if '@' in DATABASE_URL else DATABASE_URL, '***:***@')
        }

        return f"""
        <h1>Database Test ✅</h1>
        <pre>{db_info}</pre>
        <p><a href="/db-init">Initialize Database</a> | <a href="/">← Back to main page</a></p>
        """, 200

    except Exception as e:
        logger.error(f"Database test failed: {e}")
        return f"""
        <h1>Database Error ❌</h1>
        <p>Error: {str(e)}</p>
        <p>DATABASE_URL: {DATABASE_URL.replace(DATABASE_URL.split('@')[0] if '@' in DATABASE_URL else DATABASE_URL, '***:***@')}</p>
        <p><a href="/db-init">Try to Initialize Database</a> | <a href="/">← Back to main page</a></p>
        """, 500

@app.route('/db-init')
def db_init():
    """Инициализация базы данных"""
    try:
        with engine.connect() as conn:
            # Создание таблиц
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS "USER" (
                    user_id SERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    given_name VARCHAR(100) NOT NULL,
                    surname VARCHAR(100) NOT NULL,
                    city VARCHAR(100),
                    phone_number VARCHAR(20),
                    profile_description TEXT,
                    password VARCHAR(255) NOT NULL
                )
            """))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS CAREGIVER (
                    caregiver_user_id INTEGER PRIMARY KEY REFERENCES "USER"(user_id),
                    photo VARCHAR(500),
                    gender VARCHAR(10),
                    caregiving_type VARCHAR(50),
                    hourly_rate DECIMAL(10,2)
                )
            """))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS MEMBER (
                    member_user_id INTEGER PRIMARY KEY REFERENCES "USER"(user_id),
                    house_rules TEXT,
                    dependent_description TEXT
                )
            """))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS ADDRESS (
                    member_user_id INTEGER REFERENCES MEMBER(member_user_id),
                    house_number VARCHAR(20),
                    street VARCHAR(200),
                    town VARCHAR(100),
                    PRIMARY KEY (member_user_id)
                )
            """))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS JOB (
                    job_id SERIAL PRIMARY KEY,
                    member_user_id INTEGER REFERENCES MEMBER(member_user_id),
                    required_caregiving_type VARCHAR(50),
                    other_requirements TEXT,
                    date_posted DATE
                )
            """))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS JOB_APPLICATION (
                    caregiver_user_id INTEGER REFERENCES CAREGIVER(caregiver_user_id),
                    job_id INTEGER REFERENCES JOB(job_id),
                    date_applied DATE,
                    PRIMARY KEY (caregiver_user_id, job_id)
                )
            """))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS APPOINTMENT (
                    appointment_id SERIAL PRIMARY KEY,
                    caregiver_user_id INTEGER REFERENCES CAREGIVER(caregiver_user_id),
                    member_user_id INTEGER REFERENCES MEMBER(member_user_id),
                    appointment_date DATE,
                    appointment_time TIME,
                    work_hours INTEGER NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending'
                )
            """))

            conn.commit()

        return f"""
        <h1>Database Initialized ✅</h1>
        <p>All tables created successfully!</p>
        <p><a href="/db-test">Test Connection</a> | <a href="/">← Back to main page</a></p>
        """, 200

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return f"""
        <h1>Database Init Failed ❌</h1>
        <p>Error: {str(e)}</p>
        <p>DATABASE_URL: {DATABASE_URL.replace(DATABASE_URL.split('@')[0] if '@' in DATABASE_URL else DATABASE_URL, '***:***@')}</p>
        <p><a href="/db-test">Test Connection</a> | <a href="/">← Back to main page</a></p>
        """, 500

def create_crud_routes(table_name, config):
    route_name = table_name
    id_field = config['id_field']
    
    # Generate unique function names
    list_func_name = f'list_{route_name}'
    create_func_name = f'create_{route_name}'
    update_func_name = f'update_{route_name}' if id_field else None
    delete_func_name = f'delete_{route_name}'
    
    # Generate table display name
    table_display_name = table_name.replace('_', ' ').title()
    # Fix pluralization
    if table_display_name.endswith('y'):
        table_display_name = table_display_name[:-1] + 'ies'
    elif not table_display_name.endswith('s'):
        table_display_name += 's'
    
    def list_view():
        session = Session()
        try:
            result = session.execute(text(config['list_query']))
            rows = [dict(row._mapping) for row in result]
            # Handle composite key for job_applications
            if table_name == 'job_applications':
                return render_template('list.html',
                                     rows=rows, columns=config['columns'],
                                     table_name=table_display_name,
                                     create_route=create_func_name,
                                     update_route=None,
                                     delete_route=delete_func_name,
                                     id_key='caregiver_user_id', id_field='caregiver_user_id',
                                     composite_key=True, job_id_field='job_id')
            else:
                return render_template('list.html',
                                     rows=rows, columns=config['columns'],
                                     table_name=table_display_name,
                                     create_route=create_func_name,
                                     update_route=update_func_name if id_field else None,
                                     delete_route=delete_func_name,
                                     id_key=id_field, id_field=id_field)
        except SQLAlchemyError as e:
            logger.error(f"Database error in {table_name} list: {e}")
            flash(f'Database error: {str(e)}', 'error')
            return render_template('list.html',
                                 rows=[], columns=config['columns'],
                                 table_name=table_display_name,
                                 create_route=create_func_name,
                                 update_route=update_func_name if id_field else None,
                                 delete_route=delete_func_name,
                                 id_key=id_field, id_field=id_field)
        except Exception as e:
            logger.error(f"Unexpected error in {table_name} list: {e}")
            return "Internal Server Error", 500
        finally:
            session.close()
    
    list_view.__name__ = list_func_name
    app.add_url_rule(f'/{table_name}', view_func=list_view, endpoint=list_func_name)
    
    def create_view():
        if request.method == 'POST':
            session = Session()
            try:
                fields = config['insert_fields']
                values = {}
                for field in fields:
                    val = request.form.get(field)
                    if field in ['caregiver_user_id', 'member_user_id', 'job_id']:
                        values[field] = int(val) if val else None
                    elif field == 'hourly_rate':
                        values[field] = float(val) if val else None
                    elif field == 'work_hours':
                        values[field] = int(val) if val else None
                    else:
                        values[field] = val if val else None
                
                placeholders = ', '.join([f':{f}' for f in fields])
                field_names = ', '.join(fields)
                session.execute(text(f"INSERT INTO {config['table']} ({field_names}) VALUES ({placeholders})"), values)
                session.commit()
                flash(f'{table_display_name} created successfully!', 'success')
                return redirect(url_for(list_func_name))
            except Exception as e:
                session.rollback()
                flash(f'Error: {str(e)}', 'error')
            finally:
                session.close()
        
        fields = []
        for field in config['create_fields']:
            field_copy = field.copy()
            if field['type'] == 'select' and 'options_query' in field:
                field_copy['options'] = get_options_from_query(field['options_query'])
            fields.append(field_copy)
        return render_template('form.html', fields=fields, table_name=table_display_name,
                              action='Create', list_route=list_func_name)
    
    create_view.__name__ = create_func_name
    app.add_url_rule(f'/{table_name}/create', view_func=create_view, endpoint=create_func_name, methods=['GET', 'POST'])
    
    if id_field:
        def update_view(**kwargs):
            session = Session()
            try:
                record_id = kwargs.get(id_field) or request.view_args.get(id_field)
                if request.method == 'POST':
                    update_fields = config['update_fields']
                    values = {id_field: record_id}
                    for field in update_fields:
                        val = request.form.get(field)
                        if field == 'hourly_rate':
                            values[field] = float(val) if val else None
                        elif field == 'work_hours':
                            values[field] = int(val) if val else None
                        else:
                            values[field] = val if val else None
                    
                    set_clause = ', '.join([f'{f} = :{f}' for f in update_fields])
                    session.execute(text(f"UPDATE {config['table']} SET {set_clause} WHERE {id_field} = :{id_field}"), values)
                    session.commit()
                    flash(f'{table_display_name} updated successfully!', 'success')
                    return redirect(url_for(list_func_name))
                
                result = session.execute(text(f"SELECT * FROM {config['table']} WHERE {id_field} = :id"), {'id': record_id})
                row = result.fetchone()
                if not row:
                    flash('Record not found', 'error')
                    return redirect(url_for(list_func_name))
                
                row_dict = dict(row._mapping)
                fields = []
                for field in config['create_fields']:
                    if field['name'] in config['update_fields']:
                        field_copy = field.copy()
                        field_copy['value'] = row_dict.get(field['name'])
                        if field['type'] == 'select' and 'options_query' in field:
                            field_copy['options'] = get_options_from_query(field['options_query'])
                        fields.append(field_copy)
                
                return render_template('form.html', fields=fields, table_name=table_display_name,
                                     action='Update', list_route=list_func_name)
            except Exception as e:
                session.rollback()
                flash(f'Error: {str(e)}', 'error')
                return redirect(url_for(list_func_name))
            finally:
                session.close()
        
        update_view.__name__ = update_func_name
        app.add_url_rule(f'/{table_name}/<int:{id_field}>/update', view_func=update_view, endpoint=update_func_name, methods=['GET', 'POST'])
        
        def delete_view(**kwargs):
            session = Session()
            try:
                record_id = kwargs.get(id_field) or request.view_args.get(id_field)
                session.execute(text(f"DELETE FROM {config['table']} WHERE {id_field} = :id"), {'id': record_id})
                session.commit()
                flash(f'{table_display_name} deleted successfully!', 'success')
            except Exception as e:
                session.rollback()
                flash(f'Error: {str(e)}', 'error')
            finally:
                session.close()
            return redirect(url_for(list_func_name))
        
        delete_view.__name__ = delete_func_name
        app.add_url_rule(f'/{table_name}/<int:{id_field}>/delete', view_func=delete_view, endpoint=delete_func_name, methods=['POST'])
    else:
        # Special case for job_applications (composite key)
        def delete_view(**kwargs):
            session = Session()
            try:
                caregiver_id = kwargs.get('caregiver_user_id') or request.view_args.get('caregiver_user_id')
                job_id = kwargs.get('job_id') or request.view_args.get('job_id')
                session.execute(text(f"DELETE FROM {config['table']} WHERE caregiver_user_id = :c AND job_id = :j"),
                              {'c': caregiver_id, 'j': job_id})
                session.commit()
                flash(f'{table_display_name} deleted successfully!', 'success')
            except Exception as e:
                session.rollback()
                flash(f'Error: {str(e)}', 'error')
            finally:
                session.close()
            return redirect(url_for(list_func_name))
        
        delete_view.__name__ = delete_func_name
        app.add_url_rule(f'/{table_name}/<int:caregiver_user_id>/<int:job_id>/delete', view_func=delete_view, endpoint=delete_func_name, methods=['POST'])

# Generate routes for all tables
for table_name, config in TABLE_CONFIGS.items():
    create_crud_routes(table_name, config)

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug, host='0.0.0.0', port=port)
