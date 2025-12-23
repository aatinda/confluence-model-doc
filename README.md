# Sparx Enterprise Architect Model Documentation

## Generate XMI file and images.

In Sparx Enterprise Architect, click on the required namespace or package.

Go to **Publish** > **Publish As...**

Select **UML 2.1 (XML 2.1)**, ensure the appropriate export directory is selected and that the **Generate Diagram Images** option is selected with the appropriate image format.

Click **Export** to export the package.

Move the images to the `model/Images` directory and the XMI file to the `model` directory.

## Generate the model documentation markdown pages.

```
python process_model.py
```

## To generate a Confluence page from the markdown

```
export CONFLUENCE_API_KEY=<PERSONAL_TOKEN>
export CONFLUENCE_DOMAIN=<DOMAIN NAME OF CONFLUENCE INSTANCE>
export CONFLUENCE_USER_NAME=<USER NAME/EMAIL ADDRESS>

md2conf -r 1339916291 ./output
```

An alternative one-line command is:

```
md2conf -a <PERSONAL_TOKEN> -d confluence.tmr.qld.gov.au -r 179044583 -p / -s SCS output
```

Where 179044583 is the parent page ID and SCS is the space key. 
