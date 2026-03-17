#!/usr/bin/env python3
"""Plot hall-call traffic volume over time using 10-minute bins.

Usage:
  python scripts/plot_hall_call_traffic.py [input_csv] [output_png]

Defaults:
  input_csv  = hall_calls.csv
  output_png = hall_call_traffic_distribution.png
"""

import csv
import sys

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


BIN_SECONDS = 10 * 60
DAY_SECONDS = 24 * 60 * 60


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


def seconds_to_hhmm(total_seconds):
	hours = total_seconds // 3600
	minutes = (total_seconds % 3600) // 60
	return f"{hours:02d}:{minutes:02d}"


def categorize_call(origin_floor, destination_floor):
	if origin_floor > 0 and destination_floor == 0:
		return "outgoing"
	if origin_floor == 0 and destination_floor != 0:
		return "incoming"
	if origin_floor != 0 and destination_floor != 0:
		return "inter-floor"
	return None


def build_series(calls):
	num_bins = DAY_SECONDS // BIN_SECONDS
	outgoing_counts = [0] * num_bins
	interfloor_counts = [0] * num_bins
	incoming_counts = [0] * num_bins

	for t, origin_floor, destination_floor in calls:
		if t < 0 or t >= DAY_SECONDS:
			continue
		idx = t // BIN_SECONDS
		category = categorize_call(origin_floor, destination_floor)
		if category == "outgoing":
			outgoing_counts[idx] += 1
		elif category == "inter-floor":
			interfloor_counts[idx] += 1
		elif category == "incoming":
			incoming_counts[idx] += 1

	x_seconds = [i * BIN_SECONDS for i in range(num_bins)]
	return x_seconds, outgoing_counts, interfloor_counts, incoming_counts


def main():
	input_csv = sys.argv[1] if len(sys.argv) > 1 else "hall_calls.csv"
	output_png = (
		sys.argv[2] if len(sys.argv) > 2 else "hall_call_traffic_distribution.png"
	)

	calls = read_calls(input_csv)
	if not calls:
		raise ValueError(
			f"No call data found in {input_csv}. Generate hall_calls.csv by running benchmark_controller.py first."
		)

	x_seconds, outgoing_counts, interfloor_counts, incoming_counts = build_series(calls)
	bar_width = BIN_SECONDS
	x_positions = [x + (BIN_SECONDS - bar_width) / 2 for x in x_seconds]

	plt.figure(figsize=(14, 5))
	plt.bar(
		x_positions,
		incoming_counts,
		width=bar_width,
		align="edge",
		color="#50bd50",
		label="incoming",
		edgecolor="black",
		linewidth=0.25,
	)
	plt.bar(
		x_positions,
		interfloor_counts,
		width=bar_width,
		align="edge",
		bottom=incoming_counts,
		color="#eed264",
		label="inter-floor",
		edgecolor="black",
		linewidth=0.25,
	)
	incoming_plus_interfloor = [i + f for i, f in zip(incoming_counts, interfloor_counts)]
	plt.bar(
		x_positions,
		outgoing_counts,
		width=bar_width,
		align="edge",
		bottom=incoming_plus_interfloor,
		color="#df5a5a",
		label="outgoing",
		edgecolor="black",
		linewidth=0.25,
	)
	plt.title("Simulated WZ Traffic Flow")
	plt.xlabel("Time")
	plt.ylabel("Hall Calls/10 Mins")
	plt.legend()
	plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
	plt.grid(axis="y", alpha=0.25, linewidth=0.8)

	tick_positions = list(range(0, DAY_SECONDS + 1, 2 * 60 * 60))
	plt.xticks(tick_positions, [seconds_to_hhmm(t) for t in tick_positions], rotation=45)
	plt.xlim(0, DAY_SECONDS)
	plt.margins(x=0)
	plt.tight_layout()
	plt.savefig(output_png)

	print(f"Saved plot to {output_png}")


if __name__ == "__main__":
	main()
