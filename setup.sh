mkdir -p ~/.streamlit/

echo "\
[server]\n\
headless = true\n\
port = $PORT\n\
enableCORS = false\n\
enableXsrfProtection = false\n\
address = \"0.0.0.0\"\n\
\n\
" > ~/.streamlit/config.toml 