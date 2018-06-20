from flask import Flask, jsonify, request
from config import Configuration
from werkzeug.contrib.cache import MemcachedCache, SimpleCache
from datetime import datetime
import psycopg2

app = Flask(__name__)
app.config.from_object(Configuration)


conn = psycopg2.connect(
    database=app.config['PG_DB'],
    user=app.config['PG_USER'],
    password=app.config['PG_PASS'],
    host=app.config['PG_HOST'],
    port=app.config['PG_PORT']
)
cur = conn.cursor()

cache = MemcachedCache(['127.0.0.1:11211'])

STATUS_STATE = {
    'open': ['answered', 'closed'],
    'answered': ['closed', 'awaiting'],
    'awaiting': ['closed'],
    'closed': []
}


def serializer(tpl):
    descr = ('id', 'subject', 'text', 'email',
             'status', 'updated_at', 'created_at')
    if len(descr) != len(tpl):
        raise Exception('Not enough data to serialize')
    return dict(zip(descr, tpl))


def comments_serializer(coml):
    output = []
    for comment in coml:
        descr = ('email', 'text')
        if len(descr) != len(comment):
            raise Exception('Not enough data to serialize')
        output.append(dict(zip(descr, comment)))
    return output


def get_ticket_and_set(ticket_id):
    query = """SELECT * FROM tickets WHERE id=%s;"""
    cur.execute(query, (ticket_id,))
    ticket = cur.fetchone()
    if ticket is None:
        return 'No ticket with this id'
    ticket_data = serializer(ticket)
    cache.set('%s' % ticket_id, ticket_data, timeout=6000)
    return ticket_data


@app.route('/')
def index():
    urls = {
        'Create ticket': '/create_ticket/',
        'Get ticket':  '/get_ticket/<int:ticket>/',
        'Change status': '/change_status/<int:ticket>/',
        'Add comment': '/add_comment/<int:ticket>/',
    }
    return jsonify({'urls': urls})


@app.route('/create_ticket/', methods=['POST'])
def create_ticket():
    data = request.json
    subject = data.get('subject')
    text = data.get('text')
    email = data.get('email')
    status = 'open'
    updated_at = datetime.now()
    created_at = datetime.now()

    query = """INSERT INTO tickets
    (subject, text, email, status, updated_at, created_at)
    VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;"""
    cur.execute(query, (subject, text, email, status, updated_at, created_at))
    conn.commit()

    ticket_id = cur.fetchone()

    get_ticket_and_set(ticket_id[0])

    return jsonify({
        'message': 'Ticket with id: %s has been added' % ticket_id[0]
    })


@app.route('/get_ticket/<int:ticket>/', methods=['GET'])
def get_ticket(ticket):
    output = cache.get('%s' % ticket)
    if not output:
        output = get_ticket_and_set(ticket)

    query = """SELECT email, text FROM comments WHERE ticket_id=%s;"""
    cur.execute(query, (ticket,))
    comments = cur.fetchall()

    return jsonify({'ticket': output, 'comments': comments_serializer(comments)})


@app.route('/change_status/<int:ticket>/', methods=['POST'])
def change_status(ticket):
    status = request.json['status']
    if not status:
        return jsonify({'ERROR': 'No "status" in request'})

    ticket_data = cache.get('%s' % ticket)
    print 'FROM cache', ticket_data
    if ticket_data is None:
        try:
            ticket_data = get_ticket_and_set(ticket)
        except:
            return jsonify({
                'ERROR': 'Problems with getting ticket with this id'
            })
    if ticket_data.get('status') == 'closed':
        return jsonify({'ERROR': 'This ticket is closed'})

    if status not in STATUS_STATE[ticket_data.get('status')]:
        return jsonify({
            'ERROR': 'Status is not Valid',
            'Valid Statuses': STATUS_STATE})

    updated_at = datetime.now()
    query = 'UPDATE tickets SET status = %s, updated_at = %s WHERE id = %s;'
    cur.execute(query, (status, updated_at, ticket))
    conn.commit()
    get_ticket_and_set(ticket)
    return jsonify({
        'message': 'Status of ticket with id: %s has been updated' % ticket
    })


@app.route('/add_comment/<int:ticket>/', methods=['POST'])
def add_comment(ticket):
    data = request.json
    text = data.get('text')
    email = data.get('email')
    created_at = datetime.now()
    query = """INSERT INTO comments
    (ticket_id, text, email, created_at)
    VALUES (%s, %s, %s, %s);"""
    cur.execute(query, (ticket, text, email, created_at))
    conn.commit()
    return jsonify({
        'comment': 'Comment to ticket with id: %s has been added' % ticket
    })


if __name__ == '__main__':
    app.run(debug=True)
