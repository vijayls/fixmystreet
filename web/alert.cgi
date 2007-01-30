#!/usr/bin/perl -w

# alert.cgi:
# Alert code for Neighbourhood Fix-It
#
# Copyright (c) 2007 UK Citizens Online Democracy. All rights reserved.
# Email: matthew@mysociety.org. WWW: http://www.mysociety.org
#
# $Id: alert.cgi,v 1.2 2007-01-26 22:48:31 matthew Exp $

use strict;
require 5.8.0;

# Horrible boilerplate to set up appropriate library paths.
use FindBin;
use lib "$FindBin::Bin/../perllib";
use lib "$FindBin::Bin/../../perllib";
use Digest::SHA1 qw(sha1_hex);

use Page;
use mySociety::Alert;
use mySociety::AuthToken;
use mySociety::Config;
use mySociety::DBHandle qw(dbh select_all);
use mySociety::Util qw(is_valid_email);
use mySociety::Web qw(ent);

BEGIN {
    mySociety::Config::set_file("$FindBin::Bin/../conf/general");
    mySociety::DBHandle::configure(
        Name => mySociety::Config::get('BCI_DB_NAME'),
        User => mySociety::Config::get('BCI_DB_USER'),
        Password => mySociety::Config::get('BCI_DB_PASS'),
        Host => mySociety::Config::get('BCI_DB_HOST', undef),
        Port => mySociety::Config::get('BCI_DB_PORT', undef)
    );
}

sub main {
    my $q = shift;
    my $out = '';
    if (my $signed_email = $q->param('signed_email')) {
        my ($salt, $signed_email) = split /,/, $signed_email;
        my $email = $q->param('email');
        my $id = $q->param('id');
        my $secret = scalar(dbh()->selectrow_array('select secret from secret'));
        if ($signed_email eq sha1_hex("$id-$email-$salt-$secret")) {
            my $alert_id = mySociety::Alert::create($email, 'new_updates', $id);
            mySociety::Alert::confirm($alert_id);
            $out .= '<p>You have successfully subscribed to that alert.</p>';
        } else {
            $out = '<p>We could not validate that alert.</p>';
        }
    } elsif (my $token = $q->param('token')) {
        my $data = mySociety::AuthToken::retrieve('alert', $token);
        if (my $id = $data->{id}) {
            my $type = $data->{type};
            if ($type eq 'subscribe') {
                mySociety::Alert::confirm($id);
                $out = '<p>You have successfully confirmed your alert.</p>';
            } elsif ($type eq 'unsubscribe') {
                mySociety::Alert::delete($id);
                $out = '<p>You have successfully deleted your alert.</p>';
            }
        } else {
            $out = <<EOF;
<p>Thank you for trying to confirm your update or problem. We seem to have a
problem ourselves though, so <a href="/contact">please let us know what went on</a>
and we'll look into it.
EOF
        }
    } elsif (my $email = $q->param('email')) {
        my @errors;
        push @errors, 'Please enter a valid email address' unless is_valid_email($email);
        if (@errors) {
            $out = display_form($q, @errors);
        } else {
            my $type = $q->param('type');
            my $alert_id;
            if ($type eq 'updates') {
                my $id = $q->param('id');
                $alert_id = mySociety::Alert::create($email, 'new_updates', $id);
            } elsif ($type eq 'problems') {
                $alert_id = mySociety::Alert::create($email, 'new_problems');
            } else {
                throw mySociety::Alert::Error('Invalid type');
            }
            my %h = ();
            $h{url} = mySociety::Config::get('BASE_URL') . '/A/'
                . mySociety::AuthToken::store('alert', { id => $alert_id, type => 'subscribe' } );
            dbh()->commit();
            $out = Page::send_email($email, undef, 'alert-confirm', %h);
        }
    } elsif ($q->param('id')) {
        $out = display_form($q);
    } else {
        $out = '<p>Subscribe from a problem page!</p>';
    }

    print Page::header($q, 'Confirmation');
    print $out;
    print Page::footer();
}
Page::do_fastcgi(\&main);

# Updates only at present
sub display_form {
    my ($q, @errors) = @_;
    my @vars = qw(id email);
    my %input = map { $_ => $q->param($_) || '' } @vars;
    my %input_h = map { $_ => $q->param($_) ? ent($q->param($_)) : '' } @vars;
    my $out = '';
    if (@errors) {
        $out .= '<ul id="error"><li>' . join('</li><li>', @errors) . '</li></ul>';
    }
    $out .= <<EOF;
<p>Receive email when updates are left on this problem.
<form action="alert" method="post">
<label class="n" for="alert_email">Email:</label>
<input type="text" name="email" id="alert_email" value="$input_h{email}" size="30">
<input type="hidden" name="id" value="$input_h{id}">
<input type="hidden" name="type" value="updates">
<input type="submit" value="Subscribe">
</form>
EOF
    return $out;
}