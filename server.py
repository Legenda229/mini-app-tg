from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from database import *
from config_web import (MIN_GOLD, REQUIRED_SKIN, TERMS_URL, PRIVACY_URL,
                        API_SECRET, PORT)
import math

app = Flask(__name__)
CORS(app)
init_db()


def calc_skin_price(gold_amount, gold_price, commission):
    return round((gold_amount * gold_price) / (1 - commission), 2)


def check_secret():
    token = request.headers.get('X-Api-Secret', '')
    return token == API_SECRET


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/user', methods=['POST'])
def api_user():
    d = request.json
    tid = d.get('telegram_id')
    if not tid:
        return jsonify({'error': 'no id'}), 400
    u = get_or_create_user(tid, d.get('username'), d.get('first_name'),
                            d.get('last_name'), d.get('photo_url'))
    u['unread'] = unread_count(tid)
    return jsonify({'success': True, 'user': u})


@app.route('/api/price')
def api_price():
    return jsonify({
        'price_per_gold': get_gold_price(),
        'min_gold': MIN_GOLD,
        'market_commission': get_market_commission(),
        'required_skin': REQUIRED_SKIN,
        'terms_url': TERMS_URL,
        'privacy_url': PRIVACY_URL
    })


@app.route('/api/order', methods=['POST'])
def api_order():
    d = request.json
    tid = d.get('telegram_id')
    gold = d.get('gold_amount', 0)
    gid = d.get('game_id', '')
    if not tid:
        return jsonify({'error': 'no id'}), 400
    if gold < MIN_GOLD:
        return jsonify({'error': f'Минимум {MIN_GOLD} голды'}), 400
    if not gid:
        return jsonify({'error': 'Укажите игровой ID'}), 400
    gp = get_gold_price()
    mc = get_market_commission()
    price = round(gold * gp, 2)
    sp = calc_skin_price(gold, gp, mc)
    u = get_or_create_user(tid)
    oid = create_order(u['id'], tid, 'standoff2', gold, price, sp, gid)
    return jsonify({'success': True, 'order': {
        'id': oid, 'gold_amount': gold, 'price': price,
        'skin_price': sp, 'status': 'awaiting_screenshot',
        'required_skin': REQUIRED_SKIN
    }})


@app.route('/api/orders', methods=['POST'])
def api_orders():
    d = request.json
    tid = d.get('telegram_id')
    if not tid:
        return jsonify({'error': 'no id'}), 400
    return jsonify({'success': True, 'orders': get_user_orders(tid)})


@app.route('/api/promo/activate', methods=['POST'])
def api_promo():
    d = request.json
    tid = d.get('telegram_id')
    code = d.get('code', '')
    if not tid or not code:
        return jsonify({'error': 'Укажите промокод'}), 400
    return jsonify(activate_promo(code, tid))


@app.route('/api/notifications', methods=['POST'])
def api_notifs():
    d = request.json
    tid = d.get('telegram_id')
    if not tid:
        return jsonify({'error': 'no id'}), 400
    n = get_notifs(tid)
    mark_read(tid)
    return jsonify({'success': True, 'notifications': n})


@app.route('/api/reviews/pending', methods=['POST'])
def api_pending_reviews():
    d = request.json
    tid = d.get('telegram_id')
    if not tid:
        return jsonify({'error': 'no id'}), 400
    return jsonify({'success': True, 'orders': get_completed_orders_for_review(tid)})


@app.route('/api/review/submit', methods=['POST'])
def api_submit_review():
    d = request.json
    tid = d.get('telegram_id')
    oid = d.get('order_id')
    rating = d.get('rating', 5)
    comment = d.get('comment', '')
    if not tid or not oid:
        return jsonify({'error': 'missing'}), 400
    o = get_order(oid)
    if not o or o['telegram_id'] != tid:
        return jsonify({'error': 'not found'}), 400
    if o['review_submitted']:
        return jsonify({'error': 'already'}), 400
    rnum = get_next_review_number()
    cb = get_review_cashback(o['gold_amount'])
    uname = d.get('username', str(tid))
    save_review(oid, tid, uname, rating, comment, o['gold_amount'], cb, rnum)
    add_notif(tid, 'review_cashback', 'Кэшбэк за отзыв',
              f'Спасибо! +{cb} голды.', oid)
    return jsonify({'success': True, 'cashback': cb, 'review_number': rnum})


# === API для бота (из Termux) ===

@app.route('/bot/order/<int:oid>', methods=['GET'])
def bot_get_order(oid):
    if not check_secret():
        return jsonify({'error': 'forbidden'}), 403
    o = get_order(oid)
    return jsonify({'success': True, 'order': o}) if o else jsonify({'error': 'not found'}), 404


@app.route('/bot/order/<int:oid>/screenshot', methods=['POST'])
def bot_set_screenshot(oid):
    if not check_secret():
        return jsonify({'error': 'forbidden'}), 403
    d = request.json
    update_order(oid, screenshot_file_id=d.get('file_id'), status='pending_review')
    return jsonify({'success': True})


@app.route('/bot/order/<int:oid>/complete', methods=['POST'])
def bot_complete_order(oid):
    if not check_secret():
        return jsonify({'error': 'forbidden'}), 403
    d = request.json
    update_order(oid, status='completed', completed_at=datetime.now().isoformat(),
                 moderator_id=d.get('mod_id'), moderator_username=d.get('mod_name'))
    o = get_order(oid)
    if o:
        reset_rejections(o['telegram_id'])
    return jsonify({'success': True})


@app.route('/bot/order/<int:oid>/reject', methods=['POST'])
def bot_reject_order(oid):
    if not check_secret():
        return jsonify({'error': 'forbidden'}), 403
    d = request.json
    reason = d.get('reason', '')
    update_order(oid, status='rejected', moderator_id=d.get('mod_id'),
                 moderator_username=d.get('mod_name'), reject_reason=reason)
    o = get_order(oid)
    if o:
        rej = increment_rejections(o['telegram_id'])
        comp = 0
        if rej >= 3:
            comp = get_compensation(o['gold_amount'])
            add_balance(o['telegram_id'], comp)
            reset_rejections(o['telegram_id'])
        return jsonify({'success': True, 'rejections': rej, 'compensation': comp})
    return jsonify({'success': True})


@app.route('/bot/order/<int:oid>/cancel', methods=['POST'])
def bot_cancel_order(oid):
    if not check_secret():
        return jsonify({'error': 'forbidden'}), 403
    update_order(oid, status='cancelled')
    return jsonify({'success': True})


@app.route('/bot/user/<int:tid>/orders', methods=['GET'])
def bot_user_orders(tid):
    if not check_secret():
        return jsonify({'error': 'forbidden'}), 403
    return jsonify({'success': True, 'orders': get_user_orders(tid, 10)})


@app.route('/bot/user/<int:tid>', methods=['GET'])
def bot_get_user(tid):
    if not check_secret():
        return jsonify({'error': 'forbidden'}), 403
    u = get_or_create_user(tid)
    return jsonify({'success': True, 'user': u})


@app.route('/bot/user/<int:tid>/history', methods=['GET'])
def bot_user_history(tid):
    if not check_secret():
        return jsonify({'error': 'forbidden'}), 403
    return jsonify({'success': True, 'history': get_user_purchase_history(tid)})


@app.route('/bot/review', methods=['POST'])
def bot_save_review():
    if not check_secret():
        return jsonify({'error': 'forbidden'}), 403
    d = request.json
    rnum = get_next_review_number()
    cb = get_review_cashback(d['gold_amount'])
    save_review(d['order_id'], d['telegram_id'], d['username'],
                d['rating'], d['comment'], d['gold_amount'], cb, rnum)
    add_notif(d['telegram_id'], 'review_cashback', 'Кэшбэк',
              f'+{cb} голды за отзыв', d['order_id'])
    return jsonify({'success': True, 'cashback': cb, 'review_number': rnum})


@app.route('/bot/notify', methods=['POST'])
def bot_add_notif():
    if not check_secret():
        return jsonify({'error': 'forbidden'}), 403
    d = request.json
    add_notif(d['telegram_id'], d['type'], d['title'], d['message'], d.get('order_id'))
    return jsonify({'success': True})


@app.route('/bot/settings', methods=['POST'])
def bot_set_setting():
    if not check_secret():
        return jsonify({'error': 'forbidden'}), 403
    d = request.json
    set_setting(d['key'], d['value'])
    return jsonify({'success': True})


@app.route('/bot/promo/create', methods=['POST'])
def bot_create_promo():
    if not check_secret():
        return jsonify({'error': 'forbidden'}), 403
    d = request.json
    ok = create_promo(d['code'], d['gold'], d['max_act'], d.get('expires'), d.get('by'))
    return jsonify({'success': ok})


@app.route('/bot/promo/remove', methods=['POST'])
def bot_remove_promo():
    if not check_secret():
        return jsonify({'error': 'forbidden'}), 403
    d = request.json
    return jsonify({'success': remove_promo(d['code'])})


@app.route('/bot/promo/list', methods=['GET'])
def bot_promo_list():
    if not check_secret():
        return jsonify({'error': 'forbidden'}), 403
    return jsonify({'success': True, 'promos': get_all_promos()})


@app.route('/bot/staff/add', methods=['POST'])
def bot_add_staff():
    if not check_secret():
        return jsonify({'error': 'forbidden'}), 403
    d = request.json
    return jsonify({'success': add_staff(d['tid'], d['role'], d['by'])})


@app.route('/bot/staff/remove', methods=['POST'])
def bot_remove_staff():
    if not check_secret():
        return jsonify({'error': 'forbidden'}), 403
    d = request.json
    return jsonify({'success': remove_staff(d['tid'])})


@app.route('/bot/staff/list', methods=['GET'])
def bot_staff_list():
    if not check_secret():
        return jsonify({'error': 'forbidden'}), 403
    return jsonify({'success': True, 'staff': get_all_staff()})


@app.route('/bot/stats', methods=['GET'])
def bot_stats():
    if not check_secret():
        return jsonify({'error': 'forbidden'}), 403
    s = get_stats()
    s['users'] = get_user_count()
    s['price'] = get_gold_price()
    s['reviews'] = get_review_count()
    return jsonify({'success': True, 'stats': s})


@app.route('/bot/users/all', methods=['GET'])
def bot_all_users():
    if not check_secret():
        return jsonify({'error': 'forbidden'}), 403
    return jsonify({'success': True, 'users': get_all_user_ids()})


if __name__ == '__main__':
    from datetime import datetime
    app.run(host='0.0.0.0', port=PORT, debug=False)
