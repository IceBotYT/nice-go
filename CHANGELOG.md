# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Fixed
- Increased receive timeout for WS polling
- Added extra debug logging to connection_ack check

## [0.3.9] - 2024-09-21
### Added
- Added more debug logging

## [0.3.8] - 2024-08-30
### Fixed
- Loosen tenacity pin

## [0.3.7] - 2024-08-29
### Fixed
- Downgrade `tenacity` to 8.5.0, fixes dep conflict in HA

## [0.3.6] - 2024-08-29
### Fixed
- Switch to `tenacity` for retrying, should be completely backwards compatible

## [0.3.5] - 2024-08-26
### Fixed
- More fixes (see commit history)

## [0.3.4] - 2024-08-26
### Fixed
- Try to prevent more errors

## [0.3.3] - 2024-08-26
### Fixed
- Try to prevent 'Task exception was never retrieved' (again)

## [0.3.2] - 2024-08-26
### Fixed
- Try to prevent 'Task exception was never retrieved'

## [0.3.1] - 2024-08-25
### Fixed
- Fixed reconnection logic
- Detects no keepalive

## [0.3.0] - 2024-08-19
### Added
- Add listen function

## [0.2.1] - 2024-08-19
### Fixed
- Allow multiple events to be added

## [0.2.0] - 2024-08-19
### Added
- Vacation mode support
- Barrier obstruction support

## [0.1.6] - 2024-08-01
### Added
- Add extra debug logging

## [0.1.5] - 2024-07-30
### Fixed
- Reverted unpin `pycognito`
- Moved type stubs to dev dependencies

## [0.1.4] - 2024-07-29
### Changed
- Last resort: unpinning `pycognito`

## [0.1.3] - 2024-07-29
### Changed
- Made `boto3` pinned version, hopefully fixing dep conflict in HA

## [0.1.2] - 2024-07-28
### Added
- Made all barrier commands public

## [0.1.1] - 2024-07-25
### Added
- Made BarrierState and ConnectionState public

## [0.1.0] - 2024-07-25
### Added
- Initial release!

[Unreleased]: https://github.com/IceBotYT/nice-go/compare/0.3.9...master
[0.3.9]: https://github.com/IceBotYT/nice-go/compare/0.3.8...0.3.9
[0.3.8]: https://github.com/IceBotYT/nice-go/compare/0.3.7...0.3.8
[0.3.7]: https://github.com/IceBotYT/nice-go/compare/0.3.6...0.3.7
[0.3.6]: https://github.com/IceBotYT/nice-go/compare/0.3.5...0.3.6
[0.3.5]: https://github.com/IceBotYT/nice-go/compare/0.3.4...0.3.5
[0.3.4]: https://github.com/IceBotYT/nice-go/compare/0.3.3...0.3.4
[0.3.3]: https://github.com/IceBotYT/nice-go/compare/0.3.2...0.3.3
[0.3.2]: https://github.com/IceBotYT/nice-go/compare/0.3.1...0.3.2
[0.3.1]: https://github.com/IceBotYT/nice-go/compare/0.3.0...0.3.1
[0.3.0]: https://github.com/IceBotYT/nice-go/compare/0.2.1...0.3.0
[0.2.1]: https://github.com/IceBotYT/nice-go/compare/0.2.0...0.2.1
[0.2.0]: https://github.com/IceBotYT/nice-go/compare/0.1.6...0.2.0
[0.1.6]: https://github.com/IceBotYT/nice-go/compare/0.1.5...0.1.6
[0.1.5]: https://github.com/IceBotYT/nice-go/compare/0.1.4...0.1.5
[0.1.4]: https://github.com/IceBotYT/nice-go/compare/0.1.3...0.1.4
[0.1.3]: https://github.com/IceBotYT/nice-go/compare/0.1.2...0.1.3
[0.1.2]: https://github.com/IceBotYT/nice-go/compare/0.1.1...0.1.2
[0.1.1]: https://github.com/IceBotYT/nice-go/compare/0.1.0...0.1.1
[0.1.0]: https://github.com/IceBotYT/nice-go/tree/0.1.0

