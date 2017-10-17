# Add this to crontab: 0,30 * * * * python3 /home/ubuntu/foldatlas/foldatlas/monitor.py

import traceback
import os
import requests

test_url = "http://www.foldatlas.com/transcript/AT2G45180.1"
recipient = "hugh.woolfenden@jic.ac.uk"
search_str = "AT2G45180.1"


def run_test():
    try:
        response_text = requests.get( test_url ).text  # it's a file like object and works just like a file

        if search_str in response_text:
            send_mail( "FoldAtlas success", "It worked!" )
            print( "It worked!" )
        else:
            send_mail( "FoldAtlas error", response_text )
    except:
        send_mail( "FoldAtlas error", traceback.format_exc() )


def send_mail( subject, body ):
    sendmail = "/usr/sbin/sendmail"  # sendmail location

    p = os.popen( "%s -t" % sendmail, "w" )
    p.write( "To: " + recipient + "\n" )
    p.write( "From: FoldAtlas\n" )
    p.write( "Subject: " + subject + "\n" )
    p.write( "\n" )  # blank line separating headers from body
    p.write( body )

    sts = p.close()


run_test()
