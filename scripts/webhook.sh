#!/bin/bash

# using https://github.com/adnanh/webhook with the following hooks.json config
#[
#  {
#    "id": "gitlab-webhook",
#    "execute-command": "/home/oboehmer/cleu21-service/scripts/webhook.sh",
#    "command-working-directory": "/home/oboehmer/cleu21-service/scripts",
#    "pass-arguments-to-command":
#    [
#      {
#        "source": "payload",
#        "name": "object_attributes.status"
#      },
#      {
#        "source": "payload",
#        "name": "object_attributes.ref"
#      },
#      {
#        "source": "payload",
#        "name": "project.web_url"
#      },
#      {
#        "source": "payload",
#        "name": "object_attributes.id"
#      }
#    ],
#    "response-message": "Executing notify",
#    "trigger-rule":
#    {
#      "match":
#      {
#        "type": "value",
#        "value": "<removed>",
#        "parameter":
#        {
#          "source": "header",
#          "name": "X-Gitlab-Token"
#        }
#      }
#    }
#  }
#]


# pick up proxy config if run from daemon
source /etc/environment
export HTTP_PROXY HTTPS_PROXY no_proxy
FAILED='❌'
PASSED='✅'
PENDING='⌛'

STATUS=$1
BRANCH=$2
# hack as gitlab instance is behind a reverse-proxy
REPOURL=$(echo $3 | sed 's#https*://[^/]*/\(.*\)#https://10.53.217.213:40443/\1#')
ID=$4

case "$STATUS" in
  success)  icon=$PASSED ;;
  failed|canceled)  icon=$FAILED ;;
  *)  echo "skipped notification"; exit 0;;
esac

message="""$icon  Pipeline branch '$BRANCH' status ${STATUS},
<${REPOURL}/pipelines/$ID>"""

python ./notify.py --config config-webhook.yaml $message
