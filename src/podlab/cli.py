def main():
    import fire
    from .app import app
    from .mc import mc

    fire.Fire({func.__name__: func for func in [app, mc]})


if __name__ == "__main__":
    main()
