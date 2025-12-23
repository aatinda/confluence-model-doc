To generate a Confluence page from the markdown

```
export CONFLUENCE_API_KEY=<PERSONAL_TOKEN>
export CONFLUENCE_DOMAIN=<DOMAIN NAME OF CONFLUENCE INSTANCE>
export CONFLUENCE_USER_NAME=<USER NAME/EMAIL ADDRESS>

md2conf -r 1339916291 ./output
```

The working command to use with Confluence Data Center (markdown_to_confluence 0.2.7) is:

```
md2conf -a <Conflence API Key> -d confluence.tmr.qld.gov.au -r <Root Page ID> -p / -s SCS output
```
