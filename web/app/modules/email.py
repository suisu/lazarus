from urllib.parse import urljoin
import smtplib
from io import BytesIO
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from random import randint
from PIL import Image, ImageDraw, ImageFont
from app.modules.security import encryption

privKey = encryption.get_priv_keys()

class SMTPEmail():
    def __init__(self, mailServer):
        if mailServer is not None:
            self.sender = mailServer.sender
            self.pwd = mailServer.getPassword(privKey)
            self.webDomain = mailServer.web_domain
            self.smtpServer = mailServer.smtp_server
            self.smtpPort = mailServer.smtp_port
            self.userDomain = mailServer.user_domain

    def send_qr_code(self, receiver, qrcode):
        try:
            first_letter = receiver[0]
            msg = MIMEMultipart('related')
            msg['Subject'] = 'Your Two-Factor Authentication code'
            msg['From'] = self.sender
            msg['To'] = receiver
            login_page = urljoin(self.webDomain, 'login')

            user_logo = create_user_logo(first_letter)

            html = f"""\
            <html>
                <head></head>
                <body>
                <table border="0" cellspacing="0" cellpadding="0" style="padding-bottom:20px;max-wdith:516px;min-width:220px">
                    <tbody>
                        <tr>
                            <td>
                                <div style="border-style:solid;border-width:thin;border-color:#dadce0;border-radius:8px;padding:40px 20px" 
                                    align="center">
                                    <img src="cid:image1" alt="Logo" style="width:50px;height:50px;"><br>
                                    <div style="font-family:'Google Sans',Roboto,RobotoDraft,Helvetica,Arial,sans-serif;border-bottom:thin solid #dadce0;color:rgba(0,0,0,0.87);
                                        line-height:32px;padding-bottom:24px;text-align:center;word-break:break-word">
                                        <div style="font-size:24px">
                                            App password created to sign in to your account for Lazarus Scanner
                                        </div>
                                        <table align="center" style="margin-top:8px">
                                            <tbody>
                                                <tr style="line-height:normal">
                                                    <td align="right" style="padding-right:8px">
                                                        <img width="30" height="30" style="width:30px;height:30;vertical-align:sub;border-radius:50%" 
                                                            src="cid:image2" 
                                                            alt="UserLogo">
                                                    </td>
                                                    <td>
                                                        <a style="font-family:'Google Sans',Roboto,RobotoDraft,Helvetica,Arial,sans-serif;color:rgba(0,0,0,0.87);
                                                            font-size:14px;line-height:20px">{receiver}
                                                        </a>
                                                    </td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div>
                                    <div style="font-family:Roboto-Regular,Helvetica,Arial,sans-serif;font-size:14px;color:rgba(0,0,0,0.87);
                                        line-height:20px;padding-top:20px;text-align:left">
                                        You are almost done! Please start FreeOTP on your smartphone and scan the following QR Code with it:
                                            <div style="padding-top:32px;text-align:center">
                                                <img id="qrcode" src="cid:image3" alt="QR">
                                            </div>
                                            <div style="padding-top:32px;text-align:center">
                                                <a href="{login_page}"
                                                    style="font-family:'Google Sans',Roboto,RobotoDraft,Helvetica,Arial,sans-serif;line-height:16px;color:#ffffff;font-weight:400;text-decoration:none;font-size:14px;display:inline-block;padding:10px 24px;background-color:#4184f3;
                                                    border-radius:5px;min-width:90px" target="_blank">
                                                    Login
                                                </a>
                                            </div>
                                        </div>
                                        <div style="padding-top:20px;font-size:12px;line-height:16px;color:#5f6368;letter-spacing:0.3px;text-align:center">
                                            Information: During login, the OTP is valid for 30 seconds, after 30 seconds a new OTP is generated. 
                                        </div>
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </table>
                

                </body>
            </html>
            """
            # record the MIME type of text/html
            part2 = MIMEText(html, 'html')
            # attach parts into message contianer
            msg.attach(part2)

            fp = open('web/app/static/images/5235.png','rb')
            msgImage = MIMEImage(fp.read())
            fp.close()

            #define the image's ID as referenced above
            msgImage.add_header('Content-ID', '<image1>')
            msg.attach(msgImage)

            msgImage2 = MIMEImage(user_logo.getvalue())
            msgImage2.add_header('Content-ID', '<image2>')
            msg.attach(msgImage2)

            msgImage3 = MIMEImage(qrcode.getvalue())
            msgImage3.add_header('Content-ID', '<image3>')
            msg.attach(msgImage3)

            # send via SMTP
            #session = smtplib.SMTP('smtp.gmail.com', 587)
            session = smtplib.SMTP(self.smtpServer, self.smtpPort)
            session.starttls() #enable security
            session.login(self.sender, self.pwd)

            session.sendmail(self.sender, receiver, msg.as_string())
            session.quit()
            print("MFA E-Mail sent")

        except Exception as exception:
            print(repr(exception))
            raise ValueError("Error occurred: cannot send email.")

    def reset_password(self, receiver, recover_url):
        try:
            first_name = receiver.split('.')[0]
            first_letter = receiver[0]
            msg = MIMEMultipart('related')
            msg['Subject'] = 'Your Password reset code'
            msg['From'] = self.sender
            msg['To'] = receiver

            user_logo = create_user_logo(first_letter)

            html = f"""\
            <html>
                <head></head>
                <body>
                <table border="0" cellspacing="0" cellpadding="0" style="padding-bottom:20px;max-wdith:516px;min-width:220px">
                    <tbody>
                        <tr>
                            <td>
                                <div style="border-style:solid;border-width:thin;border-color:#dadce0;border-radius:8px;padding:40px 20px" 
                                    align="center">
                                    <img src="cid:image1" alt="Logo" style="width:50px;height:50px;"><br>
                                    <div style="font-family:'Google Sans',Roboto,RobotoDraft,Helvetica,Arial,sans-serif;border-bottom:thin solid #dadce0;color:rgba(0,0,0,0.87);
                                        line-height:32px;padding-bottom:24px;text-align:center;word-break:break-word">
                                        <div style="font-size:24px">
                                            You have requested resetting your password for Lazarus Scanner
                                        </div>
                                        <table align="center" style="margin-top:8px">
                                            <tbody>
                                                <tr style="line-height:normal">
                                                    <td align="right" style="padding-right:8px">
                                                        <img width="30" height="30" style="width:30px;height:30;vertical-align:sub;border-radius:50%" 
                                                            src="cid:image2" 
                                                            alt="UserLogo">
                                                    </td>
                                                    <td>
                                                        <a style="font-family:'Google Sans',Roboto,RobotoDraft,Helvetica,Arial,sans-serif;color:rgba(0,0,0,0.87);
                                                            font-size:14px;line-height:20px">{receiver}
                                                        </a>
                                                    </td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div>
                                    <div style="font-family:Roboto-Regular,Helvetica,Arial,sans-serif;font-size:14px;color:rgba(0,0,0,0.87);
                                        line-height:20px;padding-top:20px;text-align:left">
                                        Dear {first_name}, to reset your password, click on Reset button.
                                        <p>Alternatively, you can paste the following link in your browser's address bar:</p>
                                        <p>{recover_url}</p>
                                        <p>If you have not requested a password reset simply ignore this message.</p>
                                        <p>Sincerely,</p>
                                        <p>The Lazarus Security Robot</p>
                                            <div style="padding-top:32px;text-align:center">
                                                <a href="{recover_url}"
                                                    style="font-family:'Google Sans',Roboto,RobotoDraft,Helvetica,Arial,sans-serif;line-height:16px;color:#ffffff;font-weight:400;text-decoration:none;font-size:14px;display:inline-block;padding:10px 24px;background-color:#4184f3;
                                                    border-radius:5px;min-width:90px" target="_blank">
                                                    Reset
                                                </a>
                                            </div>
                                    </div>
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </table>
                </body>
            </html>
            """

            # record the MIME type of text/html
            part2 = MIMEText(html, 'html')
            # attach parts into message contianer
            msg.attach(part2)

            fp = open('web/app/static/images/5235.png','rb')
            msgImage = MIMEImage(fp.read())
            fp.close()

            #define the image's ID as referenced above
            msgImage.add_header('Content-ID', '<image1>')
            msg.attach(msgImage)

            msgImage2 = MIMEImage(user_logo.getvalue())
            msgImage2.add_header('Content-ID', '<image2>')
            msg.attach(msgImage2)

            # send via SMTP
            session = smtplib.SMTP(self.smtpServer, self.smtpPort)
            session.starttls() #enable security
            session.login(self.sender, self.pwd)

            session.sendmail(self.sender, receiver, msg.as_string())
            session.quit()
            print("Reset E-Mmail sent")

        except Exception as exception:
            print(repr(exception))
            raise ValueError("Error occurred: cannot send email.")

    def send_test(self, receiver):
        try:
            first_letter = receiver[0]
            msg = MIMEMultipart('related')
            msg['Subject'] = 'Test E-Mail from Lazarus Scanner'
            msg['From'] = self.sender
            msg['To'] = receiver

            user_logo = create_user_logo(first_letter)

            html = f"""\
            <html>
                <head></head>
                <body>
                <table border="0" cellspacing="0" cellpadding="0" style="padding-bottom:20px;max-wdith:516px;min-width:220px">
                    <tbody>
                        <tr>
                            <td>
                                <div style="border-style:solid;border-width:thin;border-color:#dadce0;border-radius:8px;padding:40px 20px" 
                                    align="center">
                                    <img src="cid:image1" alt="Logo" style="width:50px;height:50px;"><br>
                                    <div style="font-family:'Google Sans',Roboto,RobotoDraft,Helvetica,Arial,sans-serif;border-bottom:thin solid #dadce0;color:rgba(0,0,0,0.87);
                                        line-height:32px;padding-bottom:24px;text-align:center;word-break:break-word">
                                        <div style="font-size:24px">
                                            Testing Lazarus E-Mail Sending Functionality
                                        </div>
                                        <table align="center" style="margin-top:8px">
                                            <tbody>
                                                <tr style="line-height:normal">
                                                    <td align="right" style="padding-right:8px">
                                                        <img width="30" height="30" style="width:30px;height:30;vertical-align:sub;border-radius:50%" 
                                                            src="cid:image2" 
                                                            alt="UserLogo">
                                                    </td>
                                                    <td>
                                                        <a style="font-family:'Google Sans',Roboto,RobotoDraft,Helvetica,Arial,sans-serif;color:rgba(0,0,0,0.87);
                                                            font-size:14px;line-height:20px">{receiver}
                                                        </a>
                                                    </td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </table>
                </body>
            </html>
            """
            # record the MIME type of text/html
            part2 = MIMEText(html, 'html')
            # attach parts into message contianer
            msg.attach(part2)

            fp = open('web/app/static/images/5235.png','rb')
            msgImage = MIMEImage(fp.read())
            fp.close()

            #define the image's ID as referenced above
            msgImage.add_header('Content-ID', '<image1>')
            msg.attach(msgImage)

            msgImage2 = MIMEImage(user_logo.getvalue())
            msgImage2.add_header('Content-ID', '<image2>')
            msg.attach(msgImage2)

            # send via SMTP
            #session = smtplib.SMTP('smtp.gmail.com', 587)
            session = smtplib.SMTP(self.smtpServer, self.smtpPort)
            session.starttls() #enable security
            session.login(self.sender, self.pwd)

            session.sendmail(self.sender, receiver, msg.as_string())
            session.quit()
            print("Test E-Mail sent")

            return True

        except Exception as exception:
            print(repr(exception))
            return False


def create_user_logo(first_letter):
    def bkg_color_randomizer(min,max):
        return (randint(min,max), randint(min,max), randint(min,max))
    res = bkg_color_randomizer(153,255)
    W,H = (100,100)
    user_img = Image.new('RGBA', (W,H), color=res)
    d = ImageDraw.Draw(user_img)
    fnt = ImageFont.truetype('web/app/static/fonts/aliendude.ttf', size=70)
    w,h = d.textsize(first_letter, font=fnt)
    d.text(((W-w)/2,(H-h)/2), first_letter, font=fnt, fill=(1,1,1), align='center')
    output = BytesIO()
    user_img.save(output, "PNG")
    return output
