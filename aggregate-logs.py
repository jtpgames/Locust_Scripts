import json
from pathlib import Path

results = []

if __name__ == "__main__":
    for path in Path('locust-parameter-variation-logs-epew2023').rglob('v1*.log'):
        print(path)

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
    print(json_string)

    with open("aggregated_logs.log", 'w') as file_obj:
        for result in results:
            file_obj.write(f"Clients: {result['num_clients']}: "
                           f"avg: {result['mean_of_values']['avg']}, "
                           f"max: {result['mean_of_values']['max']}\n")






