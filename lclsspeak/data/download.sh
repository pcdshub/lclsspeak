#!/bin/bash

source ../../.env "" || exit 1

if [ -z "$CONFLUENCE_TOKEN" ]; then
  exit 1
fi

wget -O "$(basename "$@").html" --header="Authorization: Bearer $CONFLUENCE_TOKEN" "$@"
