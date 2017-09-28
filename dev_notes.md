# FoldAtlas Migration Development Notes

## Web site errors arising from database values being returned as bytearrays

https://dev.mysql.com/doc/relnotes/connector-python/en/news-2-0-0.html suggests that MySQL Connector/Python was changed to simplify their testing but that this results in different behaviour, specifically that Python 3 will return bytearrays now if 'raw' is set to true.
