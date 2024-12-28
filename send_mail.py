import smtplib
from email.mime.text import MIMEText

SENDER_EMAIL = "examplenamez543@gmail.com"
SENDER_PASSWORD = "mfnppwcnqlmpzymc"

def send_otp_email(email, otp):
    subject = 'Your OTP Code'
    body = f'Your OTP code is: {otp}'

    
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL 
    msg['To'] = email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, email, msg.as_string())
    except Exception as e:
        print(f'Error sending email: {str(e)}')
    
def approval_status_mail(email, name):
    subject = f'Hi, {name}  '
    body = f'{name} , Your registration is not approved by Admin. \nWait till admin approval after that u can login to ur account.\n\nor u can contact admin...\nThank YOu..'

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, email, msg.as_string())
    except Exception as e:
        print(f'Error sending email: {str(e)}')


### USER deletion or approval..
def user_deleted(email, user):
    subject = f'Hi, {user.UserName}  '
    body = f'{user.UserName} ,  \nYour ur registration is removed ...!!'

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, email, msg.as_string())
    except Exception as e:
        print(f'Error sending email: {str(e)}') 

def user_approved(email, user):
    subject = f'Hi, {user.UserName}  '
    body = f'{user.UserName} ,  \nYour  registration is approved by Admin ...!!\nNow u can login to ur Account\n\nThank YOu...!'

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = email

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, email, msg.as_string())
    except Exception as e:
        print(f'Error sending email: {str(e)}') 
