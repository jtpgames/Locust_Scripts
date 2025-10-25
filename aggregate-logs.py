import json
from pathlib import Path
import typer

app = typer.Typer()

@app.command()
def main(
    directory: str = typer.Argument(
        ...,
        help="Directory to search for log files"
    ),
    pattern: str = typer.Option(
        "*locust-parameter-variation*.log",
        "--pattern", "-p",
        help="File pattern to search for"
    )
):
    """Aggregate locust parameter variation logs."""
    results = []
    
    search_dir = Path(directory)
    if not search_dir.exists():
        typer.echo(f"Error: Directory '{directory}' does not exist", err=True)
        raise typer.Exit(1)

    for path in search_dir.rglob(pattern):
        # print(path)

        with open(path, 'r') as file_obj:
            for line in file_obj:
                if 'Clients' not in line:
                    continue

                lineAfterClients = line.split('Clients')[1]

                cleanedLine = lineAfterClients.replace('s', '')
                cleanedLine = cleanedLine.replace(',', '')
                cleanedLine = cleanedLine.replace('avg', '')
                cleanedLine = cleanedLine.replace('max', '')

                splittedLine = cleanedLine.split(':')

                clients = float(splittedLine[1])
                avg = float(splittedLine[3])
                max = float(splittedLine[4])

                # print(f"{clients}, {avg}, {max}")

                found = False
                for kv in results:
                    if kv['num_clients'] == clients:
                        kv['values'].append(
                            {
                                'avg': avg,
                                'max': max
                            }
                        )
                        found = True

                if not found:
                    results.append(
                        {
                            'num_clients': clients,
                            'values': [{'avg': avg, 'max': max}],
                            'mean_of_values': {'avg': 0, 'max': 0}
                        }
                    )

    results.sort(key=lambda r: r['num_clients'])

    for result in results:
        mean_avg = 0
        mean_max = 0
        for value in result['values']:
            mean_avg += value['avg']
            mean_max += value['max']
        mean_avg /= len(result['values'])
        mean_max /= len(result['values'])
        result['mean_of_values']['avg'] = mean_avg
        result['mean_of_values']['max'] = mean_max

    json_string = json.dumps(results, indent=2)
    # print(json_string)

    print("# Clients, Avg. Response Time, Max Response Time, Mean Avg. Response Time, Mean Max Response Time")
    for result in results:
        for value in result['values']:
            print(f"{result['num_clients']}, {value['avg']}, {value['max']}, {result['mean_of_values']['avg']}, {result['mean_of_values']['max']}")

    output_file = search_dir / "aggregated_logs.log"
    with open(output_file, 'w') as file_obj:
        for result in results:
            file_obj.write(f"Clients: {result['num_clients']}: "
                           f"avg: {result['mean_of_values']['avg']}, "
                           f"max: {result['mean_of_values']['max']}\n")

if __name__ == "__main__":
    app()






