"""Contenu des emails de réservation. Fonctions pures : aucun envoi, aucun accès base."""

from dataclasses import dataclass
from decimal import Decimal

from app.core.booking import BookingWarning
from app.core.i18n import Locale
from app.mail.base import OutgoingEmail
from app.models.booking import BookingRequest

HOTEL_NAME = "Hôtel Gérard et Francine"


@dataclass(frozen=True)
class GuestTexts:
    subject: str
    greeting: str
    intro: str
    reference: str
    room: str
    arrival: str
    departure: str
    nights: str
    guests: str
    price: str
    price_later: str
    over_capacity: str
    min_stay: str
    closing: str
    signature: str


GUEST_TEXTS: dict[Locale, GuestTexts] = {
    Locale.FR: GuestTexts(
        subject="Votre demande de réservation {reference}",
        greeting="Bonjour {name},",
        intro=(
            "Nous avons bien reçu votre demande de réservation. Elle n'est pas encore "
            "confirmée : notre réception vous recontactera rapidement pour la confirmer."
        ),
        reference="Référence",
        room="Chambre",
        arrival="Arrivée",
        departure="Départ",
        nights="{count} nuit(s)",
        guests="{adults} adulte(s), {children} enfant(s)",
        price="Prix indicatif",
        price_later="Le prix vous sera communiqué par notre réception.",
        over_capacity=(
            "Le nombre de voyageurs dépasse la capacité de cette chambre : nous vous "
            "proposerons une solution adaptée (seconde chambre ou lit supplémentaire)."
        ),
        min_stay=(
            "Le séjour minimum sur ces dates est de {count} nuits : nous reviendrons "
            "vers vous pour trouver la meilleure solution."
        ),
        closing="À très bientôt à Nosy Be,",
        signature="L'équipe de l'hôtel Gérard et Francine",
    ),
    Locale.EN: GuestTexts(
        subject="Your booking request {reference}",
        greeting="Hello {name},",
        intro=(
            "We have received your booking request. It is not confirmed yet: our "
            "reception team will get back to you shortly to confirm it."
        ),
        reference="Reference",
        room="Room",
        arrival="Arrival",
        departure="Departure",
        nights="{count} night(s)",
        guests="{adults} adult(s), {children} child(ren)",
        price="Estimated price",
        price_later="Our reception team will let you know the price.",
        over_capacity=(
            "The number of guests exceeds this room's capacity: we will suggest a "
            "suitable option (a second room or an extra bed)."
        ),
        min_stay=(
            "The minimum stay for these dates is {count} nights: we will get back to "
            "you to find the best solution."
        ),
        closing="See you soon in Nosy Be,",
        signature="The Gérard et Francine hotel team",
    ),
    Locale.IT: GuestTexts(
        subject="La sua richiesta di prenotazione {reference}",
        greeting="Buongiorno {name},",
        intro=(
            "Abbiamo ricevuto la sua richiesta di prenotazione. Non è ancora confermata: "
            "la nostra reception la ricontatterà al più presto per confermarla."
        ),
        reference="Riferimento",
        room="Camera",
        arrival="Arrivo",
        departure="Partenza",
        nights="{count} notte/i",
        guests="{adults} adulto/i, {children} bambino/i",
        price="Prezzo indicativo",
        price_later="Il prezzo le sarà comunicato dalla nostra reception.",
        over_capacity=(
            "Il numero di ospiti supera la capacità di questa camera: le proporremo "
            "una soluzione adatta (una seconda camera o un letto aggiuntivo)."
        ),
        min_stay=(
            "Il soggiorno minimo per queste date è di {count} notti: la ricontatteremo "
            "per trovare la soluzione migliore."
        ),
        closing="A presto a Nosy Be,",
        signature="Lo staff dell'hotel Gérard et Francine",
    ),
    Locale.DE: GuestTexts(
        subject="Ihre Buchungsanfrage {reference}",
        greeting="Guten Tag {name},",
        intro=(
            "Wir haben Ihre Buchungsanfrage erhalten. Sie ist noch nicht bestätigt: "
            "unsere Rezeption meldet sich in Kürze bei Ihnen, um sie zu bestätigen."
        ),
        reference="Referenz",
        room="Zimmer",
        arrival="Anreise",
        departure="Abreise",
        nights="{count} Nacht/Nächte",
        guests="{adults} Erwachsene(r), {children} Kind(er)",
        price="Voraussichtlicher Preis",
        price_later="Den Preis teilt Ihnen unsere Rezeption mit.",
        over_capacity=(
            "Die Anzahl der Gäste übersteigt die Kapazität dieses Zimmers: wir schlagen "
            "Ihnen eine passende Lösung vor (ein zweites Zimmer oder ein Zusatzbett)."
        ),
        min_stay=(
            "Der Mindestaufenthalt für diese Daten beträgt {count} Nächte: wir melden uns "
            "bei Ihnen, um die beste Lösung zu finden."
        ),
        closing="Bis bald auf Nosy Be,",
        signature="Das Team des Hotels Gérard et Francine",
    ),
}

WARNING_LABELS: dict[BookingWarning, str] = {
    BookingWarning.OVER_CAPACITY: "Capacité dépassée",
    BookingWarning.MIN_STAY_NOT_MET: "Séjour minimum non atteint",
    BookingWarning.PRICE_UNAVAILABLE: "Tarif indisponible",
}


def format_price(amount: Decimal, locale: Locale) -> str:
    if locale == Locale.EN:
        return f"€{amount:,.2f}"
    return f"{amount:,.2f} €".replace(",", "\u202f").replace(".", ",")


def guest_acknowledgement(
    booking: BookingRequest, *, min_nights_required: int | None
) -> OutgoingEmail:
    texts = GUEST_TEXTS[booking.locale]
    price_line = (
        f"{texts.price} : {format_price(booking.quoted_total, booking.locale)}"
        if booking.quoted_total is not None
        else texts.price_later
    )
    notes = []
    if BookingWarning.OVER_CAPACITY in booking.warnings:
        notes.append(texts.over_capacity)
    if BookingWarning.MIN_STAY_NOT_MET in booking.warnings and min_nights_required:
        notes.append(texts.min_stay.format(count=min_nights_required))

    lines = [
        texts.greeting.format(name=booking.guest_name),
        "",
        texts.intro,
        "",
        f"{texts.reference} : {booking.reference}",
        f"{texts.room} : {booking.room_name}",
        f"{texts.arrival} : {booking.check_in:%d/%m/%Y}",
        f"{texts.departure} : {booking.check_out:%d/%m/%Y} "
        f"({texts.nights.format(count=booking.nights_count)})",
        texts.guests.format(adults=booking.adults, children=booking.children),
        price_line,
        *(["", *notes] if notes else []),
        "",
        texts.closing,
        texts.signature,
    ]
    return OutgoingEmail(
        to=booking.email,
        subject=f"{texts.subject.format(reference=booking.reference)} | {HOTEL_NAME}",
        body="\n".join(lines),
    )


def reception_alert(
    booking: BookingRequest, *, reception_email: str, admin_base_url: str
) -> OutgoingEmail:
    warnings = [WARNING_LABELS[BookingWarning(code)] for code in booking.warnings]
    total = (
        format_price(booking.quoted_total, Locale.FR)
        if booking.quoted_total is not None
        else "non calculé"
    )
    ages = ", ".join(str(age) for age in booking.children_ages) or "non précisés"
    lines = [
        f"Nouvelle demande de réservation {booking.reference}",
        "",
        f"Client : {booking.guest_name}",
        f"Email : {booking.email}",
        f"Téléphone : {booking.phone or 'non renseigné'}"
        + (" (préfère WhatsApp)" if booking.prefers_whatsapp else ""),
        f"Langue : {booking.locale.value}",
        "",
        f"Chambre : {booking.room_name}",
        f"Du {booking.check_in:%d/%m/%Y} au {booking.check_out:%d/%m/%Y} "
        f"({booking.nights_count} nuit(s))",
        f"Voyageurs : {booking.adults} adulte(s), {booking.children} enfant(s) (âges : {ages})",
        f"Prix indicatif : {total}",
        "",
        "Avertissements : " + (", ".join(warnings) if warnings else "aucun"),
        "",
        f"Message du client : {booking.message or '(aucun)'}",
        "",
        f"Traiter la demande : {admin_base_url.rstrip('/')}/booking-requests/{booking.id}",
    ]
    return OutgoingEmail(
        to=reception_email,
        subject=f"[Réservation] {booking.reference} | {booking.guest_name}",
        body="\n".join(lines),
        reply_to=booking.email,
    )
