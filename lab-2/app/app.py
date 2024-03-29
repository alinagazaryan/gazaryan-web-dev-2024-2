from flask import Flask, render_template, request, make_response

app = Flask(__name__)
application = app

@app.route('/')
def index():
    url = request.url
    return render_template('index.html', url=url)

@app.route('/args')
def args():
    return render_template('args.html')

@app.route('/headers')
def headers():
    return render_template('headers.html')

@app.route('/cookies')
def cookies():
    response = make_response(render_template('cookies.html'))
    if 'username' in request.cookies:
        response.delete_cookie(key='username')
    else:
        response.set_cookie('username', 'student')
    return response 

@app.route('/form', methods=['get',"post"])
def form():
    return render_template('form.html')

@app.route('/calculate', methods=['get',"post"])
def calculate():
    res = ""
    if request.method == "POST":
        if not(request.form["number1"].isdigit()):
            msg = "Первое значение должно быть числом!"
            return render_template('calculate.html', msg=msg)
        if not(request.form["number2"].isdigit()):
            msg = "Второе значение должно быть числом!"
            return render_template('calculate.html', msg=msg)
        a = int(request.form["number1"])
        b = int(request.form["number2"])
        operator = request.form["operator"]
        if operator == "+":
            res = a+b
        elif operator == "-":
            res = a-b
        elif operator == "*":
            res = a*b
        elif operator == "/":
            if b==0:
                msg = "Делить на 0 нельзя!"
                return render_template('calculate.html', msg=msg)
            res = a/b
    return render_template('calculate.html', res=res)

@app.route('/phone', methods=['get', 'post'])

def phone():
    if request.method == 'POST':
        if 'phone-number' not in request.form:
            return render_template('phone_numbers.html', msg="Недопустимый ввод. Пустая форма.")

        phone = request.form['phone-number']

        if not phone.strip():  # Check if phone number is empty after stripping whitespace
            return render_template('phone_numbers.html', msg="Недопустимый ввод. Пустой номер телефона.")

        for char in "()+-. ":
            phone = phone.replace(char, '')

        if all(char.isdigit() for char in phone):
            if phone[0] == '7' and len(phone) == 11:
                result = f'8-{phone[1:4]}-{phone[4:7]}-{phone[7:9]}-{phone[9:11]}'
                return render_template('phone_numbers.html', res=result)
            elif phone[0] == '8' and len(phone) == 11:
                result = f'8-{phone[1:4]}-{phone[4:7]}-{phone[7:9]}-{phone[9:11]}'
                return render_template('phone_numbers.html', res=result)
            elif len(phone) == 10:
                result = f'8-{phone[0:3]}-{phone[3:6]}-{phone[6:8]}-{phone[8:10]}'
                return render_template('phone_numbers.html', res=result)
            else:
                return render_template('phone_numbers.html', msg="Недопустимый ввод. Неверное количество цифр.")
        else:
            return render_template('phone_numbers.html', msg="Недопустимый ввод. В номере телефона встречаются недопустимые символы.")

    return render_template('phone_numbers.html')
    
if __name__ == '__main__':
    app.run()
