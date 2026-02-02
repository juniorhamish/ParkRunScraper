from datetime import timedelta


class ParkrunnerResult:
    event_url: str
    parkrunner_url: str
    parkrunner_id: str
    time_in_seconds: int

    def __init__(self, event_url, parkrunner_url, time_in_seconds):
        self.event_url = event_url
        self.parkrunner_url = parkrunner_url
        self.time_in_seconds = time_in_seconds
        self.parkrunner_id = parkrunner_url.split("/")[-1].split("?")[0]

    def __repr__(self):
        return f"ParkrunnerResult(event_url='{self.event_url}', parkrunner_url='{self.parkrunner_url}', time_in_seconds={self.time_in_seconds}, parkrunner_id='{self.parkrunner_id}')"

    def __str__(self):
        return f"{self.parkrunner_id} - {str(timedelta(seconds=self.time_in_seconds))}"

    def __eq__(self, other):
        if not isinstance(other, ParkrunnerResult):
            return False
        return (
            self.event_url == other.event_url
            and self.parkrunner_url == other.parkrunner_url
            and self.time_in_seconds == other.time_in_seconds
            and self.parkrunner_id == other.parkrunner_id
        )

    def __hash__(self):
        return hash((self.event_url, self.parkrunner_url, self.time_in_seconds, self.parkrunner_id))
