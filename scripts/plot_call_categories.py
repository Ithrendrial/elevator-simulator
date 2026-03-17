#!/usr/bin/env python3
"""Create three category-specific hall-call plots from hall_calls.csv.

Categories:
1. incoming: origin=0, destination!=0
2. inter-floor: origin!=0, destination!=0
3. outgoing: origin!=0, destination=0
"""

import csv
import sys

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


BIN_SECONDS = 10 * 60
DAY_SECONDS = 24 * 60 * 60


def seconds_to_hhmm(total_seconds):
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours:02d}:{minutes:02d}"


def read_calls(csv_path):
    calls = []
    with open(csv_path, newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            call_time = row.get("call_time_seconds")
            origin_floor = row.get("origin_floor")
            destination_floor = row.get("destination_floor")
            if call_time in (None, "") or origin_floor in (None, "") or destination_floor in (None, ""):
                continue
            calls.append((int(call_time), int(origin_floor), int(destination_floor)))
    return calls


def is_incoming(origin_floor, destination_floor):
    return origin_floor == 0 and destination_floor != 0


def is_interfloor(origin_floor, destination_floor):
    return origin_floor != 0 and destination_floor != 0


def is_outgoing(origin_floor, destination_floor):
    return origin_floor != 0 and destination_floor == 0


def build_counts(calls, predicate):
    num_bins = DAY_SECONDS // BIN_SECONDS
    counts = [0] * num_bins

    for call_time, origin_floor, destination_floor in calls:
        if call_time < 0 or call_time >= DAY_SECONDS:
            continue
        if not predicate(origin_floor, destination_floor):
            continue
        idx = call_time // BIN_SECONDS
        counts[idx] += 1

    x_seconds = [i * BIN_SECONDS for i in range(num_bins)]
    return x_seconds, counts


def save_plot(x_seconds, counts, color, title, output_png):
    plt.figure(figsize=(14, 5))
    bar_width = BIN_SECONDS
    x_positions = [x + (BIN_SECONDS - bar_width) / 2 for x in x_seconds]
    plt.bar(
        x_positions,
        counts,
        width=bar_width,
        align="edge",
        color=color,
        edgecolor="black",
        linewidth=0.25,
    )
    plt.title(title)
    plt.xlabel("Time")
    plt.ylabel("Calls (per 10 minutes)")
    plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.grid(axis="y", alpha=0.25, linewidth=0.8)

    tick_positions = list(range(0, DAY_SECONDS + 1, 2 * 60 * 60))
    plt.xticks(tick_positions, [seconds_to_hhmm(t) for t in tick_positions], rotation=45)
    plt.xlim(0, DAY_SECONDS)
    plt.margins(x=0)
    plt.tight_layout()
    plt.savefig(output_png)


def main():
    input_csv = sys.argv[1] if len(sys.argv) > 1 else "hall_calls.csv"

    calls = read_calls(input_csv)
    if not calls:
        raise ValueError(
            f"No call data found in {input_csv}. Generate hall_calls.csv by running benchmark_controller.py first."
        )

    x_in, y_in = build_counts(calls, is_incoming)
    x_inter, y_inter = build_counts(calls, is_interfloor)
    x_out, y_out = build_counts(calls, is_outgoing)

    save_plot(
        x_in,
        y_in,
        color="#6cba6c",
        title="Incoming Calls Over Time (origin=0, destination!=0)",
        output_png="incoming_calls_over_time.png",
    )
    save_plot(
        x_inter,
        y_inter,
        color="#ead066",
        title="Inter-floor Calls Over Time (origin!=0, destination!=0)",
        output_png="interfloor_calls_over_time.png",
    )
    save_plot(
        x_out,
        y_out,
        color="#ef5a5a",
        title="Outgoing Calls Over Time (origin!=0, destination=0)",
        output_png="outgoing_calls_over_time.png",
    )

    print("Saved incoming_calls_over_time.png")
    print("Saved interfloor_calls_over_time.png")
    print("Saved outgoing_calls_over_time.png")


if __name__ == "__main__":
    main()
