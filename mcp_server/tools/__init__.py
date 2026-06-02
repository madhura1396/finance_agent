"""
mcp_server/tools/__init__.py

Makes the tools/ directory a Python package so that server.py can import
individual tool implementations with:
    from mcp_server.tools.portfolio import get_portfolio
    from mcp_server.tools.prices    import get_price_changes
    from mcp_server.tools.news      import get_relevant_news
"""
