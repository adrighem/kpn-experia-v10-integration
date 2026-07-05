# Changelog

## [3.2.4](https://github.com/adrighem/ha-kpn-experia-v10/compare/v3.2.3...v3.2.4) (2026-07-05)


### Bug Fixes

* renew router session after timeout ([1148e94](https://github.com/adrighem/ha-kpn-experia-v10/commit/1148e949fed136da3873b49c332a7da9b195a6a4)), closes [#11](https://github.com/adrighem/ha-kpn-experia-v10/issues/11)
* use NMC.Guest for guest wifi ([72d1c48](https://github.com/adrighem/ha-kpn-experia-v10/commit/72d1c4842c1824d6a858f297b889cb136c1d3047))

## [3.2.3](https://github.com/adrighem/ha-kpn-experia-v10/compare/v3.2.2...v3.2.3) (2026-06-28)


### Bug Fixes

* suppress device permission warning spam ([7ba1112](https://github.com/adrighem/ha-kpn-experia-v10/commit/7ba111282bf28fb9efbcc1b2d92aedb619f891e6)), closes [#8](https://github.com/adrighem/ha-kpn-experia-v10/issues/8)

## [3.2.2](https://github.com/adrighem/ha-kpn-experia-v10/compare/v3.2.1...v3.2.2) (2026-06-28)


### Bug Fixes

* suppress optional endpoint permission warnings ([7dbed68](https://github.com/adrighem/ha-kpn-experia-v10/commit/7dbed683dfa5dfc99b7924d6305b5e76c5114226)), closes [#8](https://github.com/adrighem/ha-kpn-experia-v10/issues/8)

## [3.2.1](https://github.com/adrighem/ha-kpn-experia-v10/compare/v3.2.0...v3.2.1) (2026-06-11)


### Bug Fixes

* harden router session handling ([3a15507](https://github.com/adrighem/ha-kpn-experia-v10/commit/3a15507d09b65163aaee08c5387690371850de08))
* harden router session handling ([771d9b2](https://github.com/adrighem/ha-kpn-experia-v10/commit/771d9b29775dbabd680a9b9f9801872688c20212))

## [3.2.0](https://github.com/adrighem/ha-kpn-experia-v10/compare/v3.1.1...v3.2.0) (2026-06-10)


### Features

* add global wifi on/off switch ([1eee7b2](https://github.com/adrighem/ha-kpn-experia-v10/commit/1eee7b254d598234fd11384c2663ab444067d572))


### Bug Fixes

* **coordinator:** resolve syntax error causing hassfest failure ([5cce72f](https://github.com/adrighem/ha-kpn-experia-v10/commit/5cce72fceb25d4f037b8cc8241ee64e03359e8b4))
* handle 196618 error when wifi radio is disabled ([2cf5b49](https://github.com/adrighem/ha-kpn-experia-v10/commit/2cf5b49100ae1fa8357d3b570eeb4f7b9a77e009))
* handle 196618 error when wifi radio is disabled ([3cb6901](https://github.com/adrighem/ha-kpn-experia-v10/commit/3cb69011567aceaf12c53e0f8e37bdc0ebccc1df)), closes [#4](https://github.com/adrighem/ha-kpn-experia-v10/issues/4)
* handle 196618 error when wifi radio is disabled ([f8e0208](https://github.com/adrighem/ha-kpn-experia-v10/commit/f8e020890cb5e7ad7bb26bcfba27cc5f39c4e6c6)), closes [#4](https://github.com/adrighem/ha-kpn-experia-v10/issues/4)
* handle 196618 error when wifi radio is disabled ([f453436](https://github.com/adrighem/ha-kpn-experia-v10/commit/f45343665293e458e94b4e0b9869a03ae8866ab8)), closes [#4](https://github.com/adrighem/ha-kpn-experia-v10/issues/4)
* **hassfest:** resolve validation failures and logic errors ([85c104f](https://github.com/adrighem/ha-kpn-experia-v10/commit/85c104ffcaefe2e15678efd71a83f80f24093423))
* **manifest:** remove invalid homeassistant key ([15850cc](https://github.com/adrighem/ha-kpn-experia-v10/commit/15850cc7e91e5a5229f226a52498add4b7eeb52a))
* move branding assets to brand/ folder for HACS validation ([f35fe82](https://github.com/adrighem/ha-kpn-experia-v10/commit/f35fe82a7d7e1e94e440dbd30cb096cb1cf0317e))
* update repository URL to ha-kpn-experia-v10 to pass HACS validation ([a538234](https://github.com/adrighem/ha-kpn-experia-v10/commit/a5382345c150199470d0846a22194f815511f923))

## [3.1.1](https://github.com/adrighem/kpn-experia-v10-integration/compare/v3.1.0...v3.1.1) (2026-05-10)


### Bug Fixes

* allow non-critical endpoints to fail on initial setup ([01027b3](https://github.com/adrighem/kpn-experia-v10-integration/commit/01027b342080261fecccd942bb8c4ad5c244a4c6))
* correct authentication service name back to sah.Device.Information ([a63816f](https://github.com/adrighem/kpn-experia-v10-integration/commit/a63816f8682736e9ec469fd6aa68c4a2a938ae69))
* correct authentication service name for new firmware ([0927fe5](https://github.com/adrighem/kpn-experia-v10-integration/commit/0927fe51a90f3c4fdb4d42994b7a7ba78b7fd5e1))
* correctly catch application-level errors (196621, 196614, 9003) to trigger session renewal ([c6c0b11](https://github.com/adrighem/kpn-experia-v10-integration/commit/c6c0b11e093dfe1f177a2d168d5d380a727bd1f4))
* correctly scope login logic inside asyncio lock ([ebc8e75](https://github.com/adrighem/kpn-experia-v10-integration/commit/ebc8e75323de65e4468d7fa2f0b69b2517dcba24))
* dataclass inheritance breaking HA core integration loading ([79eff79](https://github.com/adrighem/kpn-experia-v10-integration/commit/79eff79af87f92951f6c9822455f20487f69ef55))
* handle diverse login response structures for contextID parsing ([bd71605](https://github.com/adrighem/kpn-experia-v10-integration/commit/bd7160536980d163cf270436253043919817d9c2))
* handle partial failures gracefully without becoming unavailable or resetting state ([5cc8f54](https://github.com/adrighem/kpn-experia-v10-integration/commit/5cc8f54873d5b81c20a5f0ea3eed11211f49d715))
* re-add HTTP 403 check and exception handling for session renewal ([ab0954c](https://github.com/adrighem/kpn-experia-v10-integration/commit/ab0954c115bd5fc5d59b345c4825f1a994d4ba0d))
* restore robust original authentication handshake with fallback ([ba884ae](https://github.com/adrighem/kpn-experia-v10-integration/commit/ba884ae15b03f8e5fe7c84e143ce91802a62dee4))
* revert sensor key 'active_clients' to 'client_count' for entity backward compatibility ([b7e5177](https://github.com/adrighem/kpn-experia-v10-integration/commit/b7e5177ee6c58c8726f3711621b2e2b2720e4d9d))
* update reboot API endpoint to use NMC service ([124a7c0](https://github.com/adrighem/kpn-experia-v10-integration/commit/124a7c0d4e20b8941b249dfe8bfaa4f98f9c3448))

## [3.1.0](https://github.com/adrighem/kpn-experia-v10-integration/compare/v3.0.2...v3.1.0) (2026-05-05)


### Features

* add brand icon to README ([4ac8766](https://github.com/adrighem/kpn-experia-v10-integration/commit/4ac876660f14d44adb54ac1d93c153fc7441e1ef))
* design and implement custom brand assets (SVG icon/logo) ([e28d70b](https://github.com/adrighem/kpn-experia-v10-integration/commit/e28d70b6af17a3134427638720a351b68a5818ee))
* design custom brand assets and update documentation ([0afd840](https://github.com/adrighem/kpn-experia-v10-integration/commit/0afd84055ee97321a1b12826aa610966dc28a9e7))
* implement comprehensive router management including WAN statistics, metadata retrieval fixes, and improved device tracking ([80fb014](https://github.com/adrighem/kpn-experia-v10-integration/commit/80fb014e220080b431dc1595eaaa8a4fd223ca82))


### Bug Fixes

* resolve HACS validation issues by enabling repo features, adding topics, and providing brand assets ([18b9f75](https://github.com/adrighem/kpn-experia-v10-integration/commit/18b9f75c7ff68bf1965375655b0afa53349feaac))
