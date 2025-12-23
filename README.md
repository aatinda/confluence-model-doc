# Generating Confluence Model Documentation

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

# LOOP_THROUGH_PACKAGES

The script `test_model.py` was created as an option to loop through all packages and recreate the same hierarchical structure in Confluence.

This proved very difficult particularly with a DATEX II structured model and was ultimately parked.

The code has been preserved in this branch in case it proves useful in the future.
