from flask_mail import Message
from app import mail

def envoyer_validation(nom_complet, email, lien_validation):
    html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head><meta charset="UTF-8"></head>
    <body style="margin:0;padding:0;background:#F9FAFB;font-family:Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#F9FAFB;padding:40px 0;">
        <tr><td align="center">
          <table width="580" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:16px;overflow:hidden;border:2px solid #1A3A6B;">

            <tr>
              <td style="background:#1A3A6B;padding:32px 40px;text-align:center;">
                <h1 style="color:#fff;font-size:28px;margin:0;font-family:Georgia,serif;">SenGestion</h1>
                <p style="color:#B8860B;margin:8px 0 0;font-size:14px;letter-spacing:2px;">GESTION INTELLIGENTE POUR LES PME</p>
              </td>
            </tr>

            <tr>
              <td style="padding:40px;">
                <h2 style="color:#1A3A6B;font-size:22px;margin:0 0 16px;">Bienvenue, {nom_complet} !</h2>
                <p style="color:#1A3A6B;font-size:15px;line-height:1.6;margin:0 0 24px;">
                  Votre compte SenGestion a été créé avec succès. Cliquez sur le bouton ci-dessous pour <strong>valider votre adresse email</strong> et activer votre espace.
                </p>

                <div style="text-align:center;margin:0 0 28px;">
                  <a href="{lien_validation}"
                     style="background:#B8860B;color:#fff;padding:16px 40px;border-radius:8px;
                            text-decoration:none;font-size:16px;font-weight:700;display:inline-block;">
                    ✅ Valider mon compte
                  </a>
                </div>

                <div style="background:#E8EEF5;border:1px solid #1A3A6B;border-radius:8px;padding:14px 20px;margin:0 0 20px;">
                  <p style="margin:0;color:#1A3A6B;font-size:13px;">
                    Ou copiez ce lien dans votre navigateur :<br>
                    <span style="color:#B8860B;word-break:break-all;">{lien_validation}</span>
                  </p>
                </div>

                <p style="color:#999;font-size:12px;line-height:1.6;margin:0;">
                  Ce lien est valable 24h. Si vous n'êtes pas à l'origine de cette inscription, ignorez cet email.
                </p>
              </td>
            </tr>

            <tr>
              <td style="background:#F9FAFB;border-top:1px solid #E8EEF5;padding:20px 40px;text-align:center;">
                <p style="color:#1A3A6B;font-size:12px;margin:0;">
                  SenGestion — Gestion intelligente pour les PME sénégalaises
                </p>
              </td>
            </tr>

          </table>
        </td></tr>
      </table>
    </body>
    </html>
    """

    msg = Message(
        subject="Validez votre compte SenGestion",
        recipients=[email],
        html=html
    )
    mail.send(msg)


def envoyer_bienvenue(nom_complet, email, nom_entreprise, plan):
    html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head><meta charset="UTF-8"></head>
    <body style="margin:0;padding:0;background:#F9FAFB;font-family:Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#F9FAFB;padding:40px 0;">
        <tr><td align="center">
          <table width="580" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:16px;overflow:hidden;border:2px solid #1A3A6B;">
            <tr>
              <td style="background:#1A3A6B;padding:32px 40px;text-align:center;">
                <h1 style="color:#fff;font-size:28px;margin:0;font-family:Georgia,serif;">SenGestion</h1>
                <p style="color:#B8860B;margin:8px 0 0;font-size:14px;letter-spacing:2px;">GESTION INTELLIGENTE POUR LES PME</p>
              </td>
            </tr>
            <tr>
              <td style="padding:40px;">
                <h2 style="color:#1A3A6B;font-size:22px;margin:0 0 16px;">Compte validé, {nom_complet} !</h2>
                <p style="color:#1A3A6B;font-size:15px;line-height:1.6;margin:0 0 20px;">
                  Votre compte <strong>{nom_entreprise}</strong> est maintenant actif. Bonne gestion !
                </p>
                <div style="background:#E8EEF5;border:1px solid #1A3A6B;border-radius:8px;padding:16px 20px;margin:0 0 28px;">
                  <p style="margin:0;color:#1A3A6B;font-size:14px;">
                    <strong>Plan :</strong> {plan.capitalize()}<br>
                    <strong>Entreprise :</strong> {nom_entreprise}
                  </p>
                </div>
                <div style="text-align:center;margin:0 0 28px;">
                  <a href="http://localhost:5001/login"
                     style="background:#1A3A6B;color:#fff;padding:14px 36px;border-radius:8px;
                            text-decoration:none;font-size:15px;font-weight:600;display:inline-block;">
                    Accéder à mon espace
                  </a>
                </div>
              </td>
            </tr>
            <tr>
              <td style="background:#F9FAFB;border-top:1px solid #E8EEF5;padding:20px 40px;text-align:center;">
                <p style="color:#1A3A6B;font-size:12px;margin:0;">SenGestion — Gestion intelligente pour les PME sénégalaises</p>
              </td>
            </tr>
          </table>
        </td></tr>
      </table>
    </body>
    </html>
    """
    msg = Message(
        subject=f"Votre compte SenGestion est actif !",
        recipients=[email],
        html=html
    )
    mail.send(msg)


def envoyer_demande_signature(nom_complet, email, numero_devis, montant, objet, lien, nom_entreprise):
    montant_fmt = f"{float(montant):,.0f}".replace(",", " ")
    html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head><meta charset="UTF-8"></head>
    <body style="margin:0;padding:0;background:#F9FAFB;font-family:Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#F9FAFB;padding:40px 0;">
        <tr><td align="center">
          <table width="580" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:16px;overflow:hidden;border:2px solid #1A3A6B;">
            <tr>
              <td style="background:#1A3A6B;padding:32px 40px;text-align:center;">
                <h1 style="color:#fff;font-size:28px;margin:0;font-family:Georgia,serif;">{nom_entreprise}</h1>
                <p style="color:#B8860B;margin:8px 0 0;font-size:13px;letter-spacing:2px;">PROPULSÉ PAR SENGESTION</p>
              </td>
            </tr>
            <tr>
              <td style="padding:40px;">
                <h2 style="color:#1A3A6B;font-size:22px;margin:0 0 16px;">Devis à signer</h2>
                <p style="color:#1A3A6B;font-size:15px;line-height:1.6;margin:0 0 24px;">
                  Bonjour <strong>{nom_complet}</strong>,<br><br>
                  Veuillez trouver ci-dessous votre devis <strong>{numero_devis}</strong> à signer.
                  Cliquez sur le bouton pour consulter le devis complet et apposer votre signature électronique.
                </p>
                <div style="background:#E8EEF5;border:1px solid #1A3A6B;border-radius:8px;padding:16px 20px;margin:0 0 28px;">
                  <p style="margin:0;color:#1A3A6B;font-size:15px;">
                    <strong>Référence :</strong> {numero_devis}<br>
                    {"<strong>Objet :</strong> " + objet + "<br>" if objet else ""}
                    <strong>Montant TTC :</strong> {montant_fmt} F CFA
                  </p>
                </div>
                <div style="text-align:center;margin:0 0 28px;">
                  <a href="{lien}"
                     style="background:#B8860B;color:#fff;padding:16px 40px;border-radius:8px;
                            text-decoration:none;font-size:16px;font-weight:700;display:inline-block;">
                    ✍️ Consulter et signer le devis
                  </a>
                </div>
                <p style="color:#999;font-size:12px;line-height:1.6;margin:0;">
                  Ou copiez ce lien : <span style="color:#B8860B;word-break:break-all;">{lien}</span><br><br>
                  Ce lien est personnel et sécurisé. Si vous n'attendiez pas ce devis, ignorez cet email.
                </p>
              </td>
            </tr>
            <tr>
              <td style="background:#F9FAFB;border-top:1px solid #E8EEF5;padding:20px 40px;text-align:center;">
                <p style="color:#1A3A6B;font-size:12px;margin:0;">SenGestion — Gestion intelligente pour les PME sénégalaises</p>
              </td>
            </tr>
          </table>
        </td></tr>
      </table>
    </body>
    </html>
    """
    msg = Message(
        subject=f"Devis {numero_devis} à signer — {nom_entreprise}",
        recipients=[email],
        html=html
    )
    mail.send(msg)


def envoyer_reset_password(nom_complet, email, lien_reset):
    html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head><meta charset="UTF-8"></head>
    <body style="margin:0;padding:0;background:#F9FAFB;font-family:Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#F9FAFB;padding:40px 0;">
        <tr><td align="center">
          <table width="580" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:16px;overflow:hidden;border:2px solid #1A3A6B;">

            <tr>
              <td style="background:#1A3A6B;padding:32px 40px;text-align:center;">
                <h1 style="color:#fff;font-size:28px;margin:0;font-family:Georgia,serif;">SenGestion</h1>
                <p style="color:#B8860B;margin:8px 0 0;font-size:14px;letter-spacing:2px;">GESTION INTELLIGENTE POUR LES PME</p>
              </td>
            </tr>

            <tr>
              <td style="padding:40px;">
                <h2 style="color:#1A3A6B;font-size:22px;margin:0 0 16px;">Réinitialisation de mot de passe</h2>
                <p style="color:#1A3A6B;font-size:15px;line-height:1.6;margin:0 0 24px;">
                  Bonjour <strong>{nom_complet}</strong>,<br><br>
                  Vous avez demandé à réinitialiser votre mot de passe. Cliquez sur le bouton ci-dessous pour choisir un nouveau mot de passe.
                </p>

                <div style="text-align:center;margin:0 0 28px;">
                  <a href="{lien_reset}"
                     style="background:#B8860B;color:#fff;padding:16px 40px;border-radius:8px;
                            text-decoration:none;font-size:16px;font-weight:700;display:inline-block;">
                    🔑 Réinitialiser mon mot de passe
                  </a>
                </div>

                <div style="background:#E8EEF5;border:1px solid #1A3A6B;border-radius:8px;padding:14px 20px;margin:0 0 20px;">
                  <p style="margin:0;color:#1A3A6B;font-size:13px;">
                    Ou copiez ce lien dans votre navigateur :<br>
                    <span style="color:#B8860B;word-break:break-all;">{lien_reset}</span>
                  </p>
                </div>

                <p style="color:#999;font-size:12px;line-height:1.6;margin:0;">
                  Ce lien est valable 1h. Si vous n'avez pas demandé cette réinitialisation, ignorez cet email — votre mot de passe reste inchangé.
                </p>
              </td>
            </tr>

            <tr>
              <td style="background:#F9FAFB;border-top:1px solid #E8EEF5;padding:20px 40px;text-align:center;">
                <p style="color:#1A3A6B;font-size:12px;margin:0;">
                  SenGestion — Gestion intelligente pour les PME sénégalaises
                </p>
              </td>
            </tr>

          </table>
        </td></tr>
      </table>
    </body>
    </html>
    """

    msg = Message(
        subject="Réinitialisation de votre mot de passe SenGestion",
        recipients=[email],
        html=html
    )
    mail.send(msg)


def envoyer_confirmation_signature(nom_complet, email, numero_devis, montant, numero_facture=None):
    facture_ligne = f"""
        <div style="background:#D6EAE0;border:1px solid #145A32;border-radius:8px;padding:14px 20px;margin:20px 0;">
          <p style="margin:0;color:#145A32;font-size:15px;">
            ✅ <strong>Facture {numero_facture} générée automatiquement</strong> — vous la recevrez sous peu.
          </p>
        </div>
    """ if numero_facture else ""

    montant_fmt = f"{float(montant):,.0f}".replace(",", " ")

    html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head><meta charset="UTF-8"></head>
    <body style="margin:0;padding:0;background:#F9FAFB;font-family:Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#F9FAFB;padding:40px 0;">
        <tr><td align="center">
          <table width="580" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:16px;overflow:hidden;border:2px solid #1A3A6B;">

            <tr>
              <td style="background:#1A3A6B;padding:32px 40px;text-align:center;">
                <h1 style="color:#fff;font-size:28px;margin:0;font-family:Georgia,serif;">SenGestion</h1>
                <p style="color:#B8860B;margin:8px 0 0;font-size:14px;letter-spacing:2px;">GESTION INTELLIGENTE POUR LES PME</p>
              </td>
            </tr>

            <tr>
              <td style="padding:40px;">
                <h2 style="color:#1A3A6B;font-size:22px;margin:0 0 16px;">Devis signé avec succès !</h2>
                <p style="color:#1A3A6B;font-size:15px;line-height:1.6;margin:0 0 24px;">
                  Bonjour <strong>{nom_complet}</strong>,<br><br>
                  Votre signature électronique pour le devis <strong>{numero_devis}</strong> a bien été enregistrée.
                </p>

                <div style="background:#E8EEF5;border:1px solid #1A3A6B;border-radius:8px;padding:16px 20px;margin:0 0 20px;">
                  <p style="margin:0;color:#1A3A6B;font-size:15px;">
                    <strong>Devis :</strong> {numero_devis}<br>
                    <strong>Montant TTC :</strong> {montant_fmt} F CFA
                  </p>
                </div>

                {facture_ligne}

                <p style="color:#999;font-size:13px;line-height:1.6;margin:0;">
                  Merci pour votre confiance. Notre équipe prendra contact avec vous prochainement.
                </p>
              </td>
            </tr>

            <tr>
              <td style="background:#F9FAFB;border-top:1px solid #E8EEF5;padding:20px 40px;text-align:center;">
                <p style="color:#1A3A6B;font-size:12px;margin:0;">
                  SenGestion — Gestion intelligente pour les PME sénégalaises
                </p>
              </td>
            </tr>

          </table>
        </td></tr>
      </table>
    </body>
    </html>
    """

    msg = Message(
        subject=f"✅ Devis {numero_devis} signé — SenGestion",
        recipients=[email],
        html=html
    )
    mail.send(msg)
