"""Entry point for the packaged executable (also runs from source: py run_cpogen.py)."""
import multiprocessing

if __name__ == "__main__":
    multiprocessing.freeze_support()
    from cpogen.ui import main
    main()
