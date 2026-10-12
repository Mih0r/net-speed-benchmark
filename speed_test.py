import argparse
import sys
import time
from dataclasses import dataclass

import httpx


@dataclass(slots=True)
class BenchmarkResult:
    duration: float
    bytes_downloaded: int


class SpeedTester:
    """Измеряет сетевую задержку и скорость последовательной загрузки."""

    def __init__(
        self, url: str, iterations: int = 10, timeout: float = 30.0
    ) -> None:
        self.url = url
        self.iterations = iterations
        self.timeout = timeout

    def _measure_single_request(self, client: httpx.Client) -> BenchmarkResult:
        start_time = time.perf_counter()
        bytes_count = 0

        with client.stream('GET', self.url, follow_redirects=True) as response:
            response.raise_for_status()
            for chunk in response.iter_bytes(chunk_size=65536):
                bytes_count += len(chunk)

        duration = time.perf_counter() - start_time
        return BenchmarkResult(duration=duration, bytes_downloaded=bytes_count)

    def run(self) -> list[BenchmarkResult]:
        results: list[BenchmarkResult] = []
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Cache-Control': 'no-cache',
        }

        with httpx.Client(timeout=self.timeout, headers=headers) as client:
            for _ in range(self.iterations):
                results.append(self._measure_single_request(client))

        return results


def format_size(bytes_count: float) -> str:
    return f'{bytes_count / (1024 * 1024):.2f} МБ'


def print_summary(results: list[BenchmarkResult]) -> None:
    if not results:
        return

    total_bytes = sum(r.bytes_downloaded for r in results)
    total_time = sum(r.duration for r in results)
    avg_time = total_time / len(results)
    avg_bytes = total_bytes / len(results)
    speed_mb_s = (
        (total_bytes / (1024 * 1024)) / total_time if total_time > 0 else 0.0
    )

    print('\n=== Результаты замера ===')
    print(f'Итераций выполнено: {len(results)}')
    print(f'Среднее время запроса: {avg_time:.3f} сек')
    print(f'Средний объем ответа: {format_size(avg_bytes)}')
    print(f'Всего скачано: {format_size(total_bytes)}')
    print(f'Скорость скачивания: {speed_mb_s:.2f} МБ/с')
    print('=========================')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Скрипт последовательного замера скорости скачивания по HTTP/HTTPS.'
    )
    parser.add_argument(
        'url', type=str, help='Прямая ссылка на скачиваемый ресурс'
    )
    parser.add_argument(
        '-n',
        '--iterations',
        type=int,
        default=10,
        help='Количество последовательных запросов (по умолчанию: 10)',
    )
    parser.add_argument(
        '-t',
        '--timeout',
        type=float,
        default=30.0,
        help='Таймаут запроса в секундах (по умолчанию: 30.0)',
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tester = SpeedTester(
        url=args.url,
        iterations=args.iterations,
        timeout=args.timeout,
    )

    try:
        print(f'Запуск замера ({args.iterations} запросов) -> {args.url}')
        results = tester.run()
        print_summary(results)
    except httpx.HTTPStatusError as exc:
        print(
            f'Ошибка HTTP {exc.response.status_code}: {exc.response.url}',
            file=sys.stderr,
        )
        sys.exit(1)
    except httpx.RequestError as exc:
        print(f'Ошибка сети: {exc}', file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print('\nЗамер прерван пользователем.', file=sys.stderr)
        sys.exit(130)


if __name__ == '__main__':
    main()
