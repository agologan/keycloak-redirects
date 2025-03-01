from services.events import (
    EventProcessor,
    NamespacedIngress as i,
    KeycloakRealmClient as c,
    KeycloakRealmClientRedirect as r,
    EventType,
)


def test_process_empty_delete():
    proc = EventProcessor()
    proc.process_event(i("default", "ingressA"), None, EventType.DELETED)
    assert 0 == len(proc.ingresses)
    assert 0 == len(proc.redirects)


def test_process_add():
    proc = EventProcessor()
    proc.process_event(
        i("default", "ingressA"),
        r("master", "clientA", "uriA://"),
        EventType.ADDED,
    )
    proc.process_event(
        i("default", "ingressB"),
        r("master", "clientA", "uriB://"),
        EventType.ADDED,
    )
    proc.process_event(
        i("default", "ingressC"),
        r("master", "clientC", "uriC://"),
        EventType.ADDED,
    )
    assert {"uriA://", "uriB://"} == proc.redirects[c("master", "clientA")]
    assert {"uriC://"} == proc.redirects[c("master", "clientC")]
    assert 3 == len(proc.ingresses)


def test_process_remove():
    proc = EventProcessor()
    proc.redirects = {c("master", "clientA"): {"uriA://", "uriB://"}}
    proc.ingresses = {
        i("default", "ingressA"): r("master", "clientA", "uriA://"),
        i("default", "ingressB"): r("master", "clientA", "uriB://"),
    }

    proc.process_event(
        i("default", "ingressA"),
        None,
        EventType.DELETED,
    )

    assert {"uriB://"} == proc.redirects[c("master", "clientA")]
    assert 1 == len(proc.ingresses)

    proc.process_event(
        i("default", "ingressB"),
        r("master", "clientB", "uriB://"),
        EventType.DELETED,
    )

    assert set() == proc.redirects[c("master", "clientA")]
    assert 0 == len(proc.ingresses)


def test_process_modify():
    proc = EventProcessor()
    proc.redirects = {c("master", "clientA"): {"uriA://"}}
    proc.ingresses = {i("default", "ingressA"): r("master", "clientA", "uriA://")}

    modified = proc.process_event(
        i("default", "ingressA"),
        r("master", "clientA", "uriB://"),
        EventType.MODIFIED,
    )

    assert {"uriB://"} == proc.redirects[c("master", "clientA")]
    assert 1 == len(proc.redirects)
    assert 1 == len(proc.ingresses)
    assert {c("master", "clientA")} == modified

    modified = proc.process_event(
        i("default", "ingressA"),
        r("master", "clientB", "uriA://"),
        EventType.MODIFIED,
    )

    assert set() == proc.redirects[c("master", "clientA")]
    assert {"uriA://"} == proc.redirects[c("master", "clientB")]
    assert 1 == len(proc.ingresses)
    assert {c("master", "clientA"), c("master", "clientB")} == modified

    modified = proc.process_event(
        i("default", "ingressB"),
        r("master", "clientB", "uriB://"),
        EventType.MODIFIED,
    )

    assert {"uriA://", "uriB://"} == proc.redirects[c("master", "clientB")]
    assert 2 == len(proc.ingresses)
    assert {c("master", "clientB")} == modified

    modified = proc.process_event(
        i("default", "ingressA"),
        r("master", "clientA", "uriA://"),
        EventType.MODIFIED,
    )

    assert {"uriA://"} == proc.redirects[c("master", "clientA")]
    assert {"uriB://"} == proc.redirects[c("master", "clientB")]
    assert 2 == len(proc.ingresses)
    assert {c("master", "clientA"), c("master", "clientB")} == modified

    modified = proc.process_event(
        i("default", "ingressA"),
        None,
        EventType.MODIFIED,
    )

    assert set() == proc.redirects[c("master", "clientA")]
    assert 1 == len(proc.ingresses)
    assert {c("master", "clientA")} == modified
