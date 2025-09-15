# main.py
from utils.loader import load_graph_from_default
import time

def demo():
    rg = load_graph_from_default()
    rg.print_summary()

    # demo: reserve first block of T1
    t1 = rg.get_track("T1")
    if t1:
        b0 = t1.blocks[0]
        print("\nTrying to occupy", b0.block_id)
        ok = b0.occupy("EXP100", entry_time=0.0, expected_exit_time=300.0)
        print("occupied ok:", ok)
        rg.print_summary()

        print("\nReleasing block")
        b0.release()
        rg.print_summary()

if __name__ == "__main__":
    demo()
