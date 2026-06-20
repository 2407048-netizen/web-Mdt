class WhatsAppGateway:
    """
    Mockup layanan pengiriman pesan WhatsApp otomatis.
    Hubungkan ke Fonnte / Wablas / Zenziva untuk produksi.
    """
    def send_message(self, phone: str, message: str):
        phone = phone.replace('+', '').replace('-', '').replace(' ', '')
        if phone.startswith('0'):
            phone = '62' + phone[1:]
        print(f"\n[WA_MOCK] → {phone}\n{message}\n{'─'*40}")
        return True

    def send_absence_alert(self, student_name: str, parent_phone: str, absence_date: str):
        msg = (
            f"Assalamu'alaikum Wr. Wb.\n\n"
            f"Kepada Yth. Orang Tua/Wali dari ananda *{student_name}*,\n\n"
            f"Kami informasikan bahwa ananda tercatat *TIDAK HADIR (Alpa)* "
            f"pada kegiatan belajar MDT Miftahul Hidayah pada tanggal *{absence_date}* "
            f"tanpa keterangan.\n\n"
            f"Mohon konfirmasi kepada pengurus madrasah jika ada keterangan lebih lanjut.\n\n"
            f"Jazakumullahu Khairan,\n"
            f"_Pengurus MDT Miftahul Hidayah_"
        )
        return self.send_message(parent_phone, msg)

    def send_billing_reminder(self, student_name: str, parent_phone: str,
                               amount: int, due_date: str):
        msg = (
            f"Assalamu'alaikum Wr. Wb.\n\n"
            f"Kepada Yth. Orang Tua/Wali dari ananda *{student_name}*,\n\n"
            f"Tagihan *SPP bulan ini* sebesar *Rp {amount:,}* "
            f"sudah dapat dibayarkan dengan batas waktu *{due_date}*.\n\n"
            f"Terima kasih atas perhatiannya.\n\n"
            f"_Pengurus MDT Miftahul Hidayah_"
        )
        return self.send_message(parent_phone, msg)
