import environ
from flask import Flask
import requests
import json
from datetime import timedelta

application = Flask(__name__)
env = environ.Env()

application.config["CONSUL_API"] = env('CONSUL_API', default='http://consul:8500/')
application.config["VAULT_API"] = env('VAULT_API', default='http://vault:8200/')
application.config["JENKINS_URL"] = env('JENKINS_URL', default='http://jenkins:8080/')
application.config["POWERDNS_URL"] = env('POWERDNS_URL', default='http://powerdns/')
application.config["POWERDNS_API_KEY"] = env('POWERDNS_API_KEY', default='')
application.config["PROXY_ADDR"] = env('PROXY_ADDR', default='proxy')
application.config["GITLAB_URL"] = env('GITLAB_URL', default='https://gitlab/-/liveness')
application.config["SENTRY_URL"] = env('SENTRY_URL', default='https://sentry/')
application.config["SENTRY_EXTERNAL_URL"] = env('SENTRY_EXTERNAL_URL', default='https://raven/')

@application.route("/")
def status():
    service_degraded = 0
    totaltime = timedelta()
    error_msg = ''

    try:
        consul_status = requests.get(application.config["CONSUL_API"] + '/v1/status/leader')
        consul_status.close()
        totaltime += consul_status.elapsed
        if consul_status.status_code != 200:
            error_msg = error_msg + '<error>consul: ' + str(consul_status.status_code) + '</error>'
            service_degraded += 1
    except requests.exceptions.RequestException as e:
        print(e)
        error_msg = error_msg + e
        service_degraded += 1

    try:
        vault_status = requests.get(application.config["VAULT_API"] + '/v1/sys/health')
        vault_status.close()
        totaltime += vault_status.elapsed
        if vault_status.status_code != 200:
            error_msg = error_msg + '<error>vault: ' + str(vault_status.status_code) + '</error>'
            service_degraded += 1
    except requests.exceptions.RequestException as e:
        print(e)
        error_msg = error_msg + e
        service_degraded += 1

    try:
        jenkins_status = requests.get(application.config["JENKINS_URL"])
        jenkins_status.close()
        totaltime += jenkins_status.elapsed
        if jenkins_status.status_code != 200:
            error_msg = error_msg + '<error>jenkins: ' + str(jenkins_status.status_code) + '</error>'
            service_degraded += 1
    except requests.exceptions.RequestException as e:
        print(e)
        error_msg = error_msg + e
        service_degraded += 1

    try:
        powerdns_headers = {'X-API-Key': application.config["POWERDNS_API_KEY"]}
        powerdns_status = requests.get(application.config["POWERDNS_URL"] + '/api/v1/servers/localhost/zones', headers=powerdns_headers)
        powerdns_status.close()
        powerdns_status_json = json.loads(powerdns_status.content)
        totaltime += powerdns_status.elapsed
        if powerdns_status.status_code != 200 or len(powerdns_status_json) < 1:
            error_msg = error_msg + '<error>powerdns: ' + str(powerdns_status.status_code) + '</error>'
            service_degraded += 1
    except requests.exceptions.RequestException as e:
        print(e)
        error_msg = error_msg + e
        service_degraded += 1

    try:
        proxy = { 'http': 'http://' + application.config["PROXY_ADDR"] + ':80', 'https': 'https://' + application.config["PROXY_ADDR"] + ':443' }
        proxy_status = requests.get('http://trade.gov.uk/', proxies=proxy, allow_redirects=False)
        proxy_status.close()
        totaltime += proxy_status.elapsed
        if proxy_status.status_code >= 399 or proxy_status.elapsed.total_seconds() > 5:
            error_msg = error_msg + '<error>proxy: ' + str(proxy_status.status_code) + '</error>'
            service_degraded += 1
    except requests.exceptions.RequestException as e:
        print(e)
        error_msg = error_msg + e
        service_degraded += 1

    try:
        gitlab_status = requests.get(application.config["GITLAB_URL"])
        gitlab_status.close()
        totaltime += gitlab_status.elapsed
        gitlab_status_json = json.loads(gitlab_status.content)
        if gitlab_status.status_code != 200 or gitlab_status_json['status'] != 'ok':
            error_msg = error_msg + '<error>gitlab: ' + str(gitlab_status.status_code) + '</error>'
            service_degraded += 1
    except requests.exceptions.RequestException as e:
        print(e)
        error_msg = error_msg + e
        service_degraded += 1

    try:
        sentry_status = requests.get(application.config["SENTRY_URL"])
        sentry_status.close()
        totaltime += sentry_status.elapsed
        if sentry_status.status_code >= 399 or sentry_status.elapsed.total_seconds() > 5:
            error_msg = error_msg + '<error>sentry: ' + str(sentry_status.status_code) + '</error>'
            service_degraded += 1
    except requests.exceptions.RequestException as e:
        print(e)
        error_msg = error_msg + e
        service_degraded += 1

    try:
        raven_status = requests.get(application.config["SENTRY_EXTERNAL_URL"])
        raven_status.close()
        totaltime += raven_status.elapsed
        if raven_status.status_code >= 499 or raven_status.elapsed.total_seconds() > 5:
            error_msg = error_msg + '<error>sentry external: ' + str(raven_status.status_code) + '</error>'
            service_degraded += 1
    except requests.exceptions.RequestException as e:
        print(e)
        error_msg = error_msg + e
        service_degraded += 1


    if service_degraded == 0:
        return('<pingdom_http_custom_check><status>OK</status><response_time>' + str(totaltime.total_seconds()) + '</response_time></pingdom_http_custom_check>')
    elif service_degraded == 3:
        return('<pingdom_http_custom_check><status>DOWN</status><response_time>' + str(totaltime.total_seconds()) + '</response_time></pingdom_http_custom_check>' + error_msg)
    elif service_degraded < 3:
        return('<pingdom_http_custom_check><status>DEGRADED</status><response_time>' + str(totaltime.total_seconds()) + '</response_time></pingdom_http_custom_check>' + error_msg)


if __name__ == "__main__":
    application.run(host='0.0.0.0')
