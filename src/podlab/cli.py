def main():
    import fire
    from .app import app
    from .mc import mc
    from .weblog import weblog

    fire.Fire({func.__name__: func for func in [app, mc, weblog]})


if __name__ == "__main__":
    main()
